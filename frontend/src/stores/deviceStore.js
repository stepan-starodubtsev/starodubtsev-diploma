// src/stores/deviceStore.js
import { makeObservable, observable, action, runInAction, computed } from 'mobx';
import {
    getAllDevices,
    createDevice,
    getDeviceById,
    updateDevice,
    deleteDevice,
    getDeviceStatus,
    configureDeviceSyslog,
    configureDeviceNetflow,
    blockIpOnDevice, // Перейменовано з getBlockIpPayload для ясності
    unblockIpOnDevice,
    getDeviceFirewallRules,
} from '../api/deviceApi'; // Переконайся, що шлях правильний

class DeviceStore {
    devices = []; // Список всіх пристроїв
    currentDevice = null; // Деталі одного вибраного пристрою
    firewallRules = []; // Правила файрволу для поточного пристрою

    isLoading = false;
    error = null;

    // Стан для пагінації таблиці пристроїв
    pagination = {
        count: 0,    // Загальна кількість записів (буде оновлюватися з API, якщо він це підтримує)
        page: 0,     // Поточна сторінка (нумерація з 0)
        rowsPerPage: 10, // Кількість рядків на сторінці
    };

    constructor() {
        makeObservable(this, {
            devices: observable.struct, // .struct для масивів об'єктів
            currentDevice: observable.deep, // .deep для об'єктів
            firewallRules: observable.struct,
            isLoading: observable,
            error: observable,
            pagination: observable.deep,

            fetchDevices: action,
            fetchDeviceById: action,
            addDevice: action,
            saveDevice: action,
            removeDevice: action,
            clearCurrentDevice: action,
            setPagination: action,

            runGetDeviceStatus: action,
            runConfigureSyslog: action,
            runConfigureNetflow: action,
            runBlockIp: action,
            runUnblockIp: action,
            fetchFirewallRulesForDevice: action,

            totalDevices: computed,
            // ... інші обчислювані властивості, якщо потрібні
        });
    }

    // Дія для оновлення параметрів пагінації
    setPagination(page, rowsPerPage) {
        this.pagination.page = page;
        this.pagination.rowsPerPage = rowsPerPage;
        this.fetchDevices(); // Перезавантажити дані для нової сторінки/розміру
    }

    get totalDevices() {
        return this.pagination.count; // Або this.devices.length, якщо пагінація на клієнті
    }

    clearCurrentDevice() {
        this.currentDevice = null;
        this.firewallRules = [];
    }

    async fetchDevices() {
        this.isLoading = true;
        this.error = null;
        try {
            // Для пагінації на сервері, API має приймати skip/limit
            // і повертати загальну кількість елементів.
            // Поки що, наш getAllDevices приймає skip/limit, але не повертає total.
            // Якщо API не повертає total, пагінація MUI TablePagination буде працювати
            // тільки для поточного завантаженого набору даних.
            const skip = this.pagination.page * this.pagination.rowsPerPage;
            const limit = this.pagination.rowsPerPage;

            const data = await getAllDevices(skip, limit); // Припускаємо, що повертає масив
            runInAction(() => {
                this.devices = data; // Припустимо, що API повертає масив пристроїв для поточної сторінки
                // Якщо API повертає об'єкт типу { items: [], total: X }:
                // this.devices = data.items;
                // this.pagination.count = data.total;

                // Тимчасово, якщо API не повертає total count, і ми хочемо пагінацію на клієнті
                // (не рекомендується для великих наборів даних):
                // this.pagination.count = data.length; // Це буде працювати тільки якщо getAllDevices завантажує ВСІ пристрої
                this.isLoading = false;
            });
        } catch (error) {
            runInAction(() => {
                this.error = error.message || "Failed to fetch devices";
                this.isLoading = false;
            });
        }
    }

    async fetchDeviceById(deviceId) {
        this.isLoading = true;
        this.error = null;
        this.currentDevice = null; // Скидаємо перед завантаженням
        try {
            const data = await getDeviceById(deviceId);
            runInAction(() => {
                this.currentDevice = data;
                this.isLoading = false;
            });
            return data;
        } catch (error) {
            runInAction(() => {
                this.error = error.message || `Failed to fetch device ${deviceId}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async addDevice(deviceData) {
        this.isLoading = true;
        this.error = null;
        try {
            const newDevice = await createDevice(deviceData);
            runInAction(() => {
                // Оскільки у нас може бути пагінація, краще перезавантажити поточну сторінку,
                // або додати логіку для додавання в список, якщо це перша сторінка.
                // Найпростіше - перезавантажити.
                this.fetchDevices();
                this.isLoading = false;
            });
            return newDevice;
        } catch (error) {
            runInAction(() => {
                this.error = error.message || "Failed to create device";
                this.isLoading = false;
            });
            throw error;
        }
    }

    async saveDevice(deviceId, deviceUpdateData) {
        this.isLoading = true;
        this.error = null;
        try {
            const updatedDevice = await updateDevice(deviceId, deviceUpdateData);
            runInAction(() => {
                // Оновлюємо пристрій у списку devices, якщо він там є
                const index = this.devices.findIndex(dev => dev.id === deviceId);
                if (index !== -1) {
                    this.devices[index] = updatedDevice;
                }
                // Оновлюємо currentDevice, якщо це він
                if (this.currentDevice && this.currentDevice.id === deviceId) {
                    this.currentDevice = updatedDevice;
                }
                this.isLoading = false;
            });
            return updatedDevice;
        } catch (error) {
            runInAction(() => {
                this.error = error.message || `Failed to update device ${deviceId}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async removeDevice(deviceId) {
        this.isLoading = true;
        this.error = null;
        try {
            await deleteDevice(deviceId);
            runInAction(() => {
                // Видаляємо пристрій зі списку
                this.devices = this.devices.filter(dev => dev.id !== deviceId);
                // Оновлюємо загальну кількість, якщо пагінація на клієнті
                // або перезавантажуємо дані, якщо пагінація на сервері
                this.pagination.count = Math.max(0, this.pagination.count -1);
                if (this.devices.length === 0 && this.pagination.page > 0) {
                    this.pagination.page -=1; // Перехід на попередню сторінку, якщо поточна стала порожньою
                }
                this.fetchDevices(); // Перезавантажуємо поточну сторінку

                if (this.currentDevice && this.currentDevice.id === deviceId) {
                    this.currentDevice = null;
                }
                this.isLoading = false;
            });
        } catch (error) {
            runInAction(() => {
                this.error = error.message || `Failed to delete device ${deviceId}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    // --- Дії з конфігурацією пристрою ---
    async runGetDeviceStatus(deviceId) {
        this.isLoading = true; // Можна додати окремий isLoading для статусу
        this.error = null;
        try {
            const statusData = await getDeviceStatus(deviceId);
            runInAction(() => {
                // Оновлюємо пристрій у списку та/або currentDevice
                const index = this.devices.findIndex(dev => dev.id === deviceId);
                if (index !== -1) {
                    this.devices[index] = { ...this.devices[index], ...statusData };
                }
                if (this.currentDevice && this.currentDevice.id === deviceId) {
                    this.currentDevice = { ...this.currentDevice, ...statusData };
                }
                this.isLoading = false;
            });
            return statusData;
        } catch (error) {
            runInAction(() => {
                this.error = error.message || `Failed to get status for device ${deviceId}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async runConfigureSyslog(deviceId, syslogConfigData) {
        // ... (аналогічно: isLoading, error, виклик API, оновлення стану пристрою, якщо потрібно)
        this.isLoading = true; this.error = null;
        try {
            const result = await configureDeviceSyslog(deviceId, syslogConfigData);
            runInAction(() => {
                this.isLoading = false;
                // Можливо, оновити прапорець syslog_configured_by_siem у пристрої, якщо API це повертає
                // Або просто перезавантажити дані пристрою: this.fetchDeviceById(deviceId) або this.runGetDeviceStatus(deviceId)
                if (result.success) this.runGetDeviceStatus(deviceId); // Оновити статус та інфо
            });
            return result;
        } catch (error) {
            runInAction(() => { this.error = error.message || "Syslog config failed"; this.isLoading = false; });
            throw error;
        }
    }

    async runConfigureNetflow(deviceId, netflowConfigData) {
        // ... (аналогічно)
        this.isLoading = true; this.error = null;
        try {
            const result = await configureDeviceNetflow(deviceId, netflowConfigData);
            runInAction(() => {
                this.isLoading = false;
                if (result.success) this.runGetDeviceStatus(deviceId);
            });
            return result;
        } catch (error) {
            runInAction(() => { this.error = error.message || "Netflow config failed"; this.isLoading = false; });
            throw error;
        }
    }

    async runBlockIp(deviceId, blockIpPayload) {
        // ... (аналогічно)
        this.isLoading = true; this.error = null;
        try {
            const result = await blockIpOnDevice(deviceId, blockIpPayload);
            runInAction(() => { this.isLoading = false; });
            return result;
        } catch (error) {
            runInAction(() => { this.error = error.message || "Block IP failed"; this.isLoading = false; });
            throw error;
        }
    }

    async runUnblockIp(deviceId, unblockIpPayload) {
        // ... (аналогічно)
        this.isLoading = true; this.error = null;
        try {
            const result = await unblockIpOnDevice(deviceId, unblockIpPayload);
            runInAction(() => { this.isLoading = false; });
            return result;
        } catch (error) {
            runInAction(() => { this.error = error.message || "Unblock IP failed"; this.isLoading = false; });
            throw error;
        }
    }

    async fetchFirewallRulesForDevice(deviceId, chain = null) {
        this.isLoading = true;
        this.error = null;
        try {
            const rules = await getDeviceFirewallRules(deviceId, chain);
            runInAction(() => {
                this.firewallRules = rules;
                this.isLoading = false;
            });
            return rules;
        } catch (error) {
            runInAction(() => {
                this.error = error.message || `Failed to fetch firewall rules for device ${deviceId}`;
                this.isLoading = false;
            });
            throw error;
        }
    }
}

const deviceStore = new DeviceStore();
export default deviceStore;