// src/stores/indicatorStore.js
import {makeObservable, observable, action, runInAction, computed} from 'mobx';
import {
    getAllIoCs,
    getIoCsCreatedToday,
    searchIoCs,
    addManualIoC,
    getIoCById,
    updateIoC,
    deleteIoC,
    linkIoCToApt, loadIoCsSources, loadIoCsUniqueTags,
} from '../api/indicatorApi';
// Може знадобитися для отримання списку APT для вибору при редагуванні IoC
// import aptGroupStore from './aptGroupStore';

class IndicatorStore {
    iocs = [];
    currentIoC = null; // Для форми редагування або деталей

    isLoading = false;
    error = null;
    operationStatus = ''; // Для повідомлень про успіх/невдачу операцій

    pagination = {
        count: 0, // Загальна кількість IoC (якщо API повертає)
        page: 0,
        rowsPerPage: 10,
        // Для фільтрації та пошуку
        searchValue: '',
        searchType: null, // IoCTypeEnum value
        filterDate: null, // 'all', 'today'
    };

    constructor() {
        makeObservable(this, {
            iocs: observable.struct,
            currentIoC: observable.deep,
            isLoading: observable,
            error: observable,
            operationStatus: observable,
            pagination: observable.deep,

            loadIoCs: action, // Загальний метод для завантаження
            fetchIoCById: action,
            createIoC: action,
            saveIoC: action,
            removeIoC: action,
            performLinkIoCToApt: action,
            clearCurrentIoC: action,
            setPagination: action,
            setSearchFilters: action,
            loadSourceNames: action,
            loadUniqueTags: action,

            totalIoCs: computed,
            displayableIoCs: computed, // Може фільтрувати/сортувати iocs
        });
    }

    // --- Управління пагінацією та фільтрами ---
    setPagination(page, rowsPerPage) {
        this.pagination.page = page;
        this.pagination.rowsPerPage = rowsPerPage;
        this.loadIoCs();
    }

    setSearchFilters(searchValue, searchType, filterDate = 'all') {
        this.pagination.searchValue = searchValue;
        this.pagination.searchType = searchType;
        this.pagination.filterDate = filterDate;
        this.pagination.page = 0; // Скидаємо на першу сторінку при новому пошуку/фільтрі
        this.loadIoCs();
    }

    get totalIoCs() {
        return this.pagination.count; // Або this.iocs.length для клієнтської пагінації
    }

    get displayableIoCs() {
        // Якщо пагінація на клієнті, тут можна реалізувати фільтрацію та сортування
        // на основі this.pagination.searchValue, searchType тощо.
        // Для серверної пагінації, цей computed може просто повертати this.iocs
        return this.iocs;
    }

    clearCurrentIoC() {
        this.currentIoC = null;
    }

    // --- Основні дії ---
    async loadIoCs() {
        this.isLoading = true;
        this.error = null;
        const {page, rowsPerPage, searchValue, searchType, filterDate} = this.pagination;
        const skip = page * rowsPerPage;
        const limit = rowsPerPage;

        try {
            let data;
            if (searchValue) {
                data = await searchIoCs(searchValue, searchType); // Пошук зазвичай не пагінується так просто
                                                                  // або API пошуку має підтримувати skip/limit
            } else if (filterDate === 'today') {
                data = await getIoCsCreatedToday(skip, limit);
            } else { // 'all' або не вказано
                data = await getAllIoCs(skip, limit);
            }

            runInAction(() => {
                this.iocs = data; // Припускаємо, що API повертає масив
                // Якщо API повертає { items: [], total: X } для пагінації:
                // this.iocs = data.items;
                // this.pagination.count = data.total;
                this.isLoading = false;
            });
        } catch (error) {
            runInAction(() => {
                this.error = error.message || "Failed to load IoCs";
                this.isLoading = false;
            });
        }
    }

    async fetchIoCById(iocEsId) {
        this.isLoading = true;
        this.error = null;
        try {
            const data = await getIoCById(iocEsId);
            runInAction(() => {
                this.currentIoC = data;
                this.isLoading = false;
            });
            return data;
        } catch (error) {
            runInAction(() => {
                this.error = error.message || `Failed to fetch IoC ${iocEsId}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async createIoC(iocData) { // iocData - це об'єкт IoCCreate
        this.isLoading = true;
        this.error = null;
        try {
            const newIoC = await addManualIoC(iocData); // API функція
            runInAction(() => {
                this.loadIoCs(); // Оновити список
                this.operationStatus = `IoC "${newIoC.value}" успішно створено.`;
                this.isLoading = false;
            });
            return newIoC;
        } catch (error) {
            runInAction(() => {
                this.error = error.detail || error.message || "Failed to create IoC";
                this.operationStatus = `Помилка створення IoC: ${this.error}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async saveIoC(iocEsId, iocUpdateData) {
        this.isLoading = true;
        this.error = null;
        try {
            const updatedIoC = await updateIoC(iocEsId, iocUpdateData);
            runInAction(() => {
                const foundedIocIndex = this.iocs.findIndex(
                    ioc => ioc.ioc_id === iocEsId
                );

                if (foundedIocIndex !== -1) {
                    this.iocs[foundedIocIndex] = updatedIoC;
                } else {
                    this.loadIoCs()
                    console.warn(`Could not find IoC with ID ${iocEsId} in the local store to update.`)
                }

                this.operationStatus = `IoC ID "${iocEsId}" успішно оновлено.`;
                this.isLoading = false;
            });
            return updatedIoC;
        } catch (error) {
            runInAction(() => {
                this.error = error.detail || error.message || `Failed to update IoC ${iocEsId}`;
                this.operationStatus = `Помилка оновлення IoC: ${this.error}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async removeIoC(iocEsId) {
        this.isLoading = true;
        this.error = null;
        try {
            await deleteIoC(iocEsId);
            runInAction(() => {
                this.loadIoCs(); // Оновити список
                if (this.currentIoC && this.currentIoC.ioc_id === iocEsId) {
                    this.currentIoC = null;
                }
                this.operationStatus = `IoC ID "${iocEsId}" успішно видалено.`;
                this.isLoading = false;
            });
        } catch (error) {
            runInAction(() => {
                this.error = error.detail || error.message || `Failed to delete IoC ${iocEsId}`;
                this.operationStatus = `Помилка видалення IoC: ${this.error}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async performLinkIoCToApt(iocEsId, aptGroupId) {
        this.isLoading = true; // Можна мати окремий isLinkingApt
        this.error = null;
        try {
            const updatedIoC = await linkIoCToApt(iocEsId, aptGroupId);
            runInAction(() => {
                // Оновити IoC у списку або currentIoC
                const index = this.iocs.findIndex(ioc => ioc.ioc_id === iocEsId);
                if (index !== -1) {
                    this.iocs[index] = updatedIoC;
                }
                if (this.currentIoC && this.currentIoC.ioc_id === iocEsId) {
                    this.currentIoC = updatedIoC;
                }
                this.operationStatus = `IoC ${iocEsId} успішно прив'язано до APT ID ${aptGroupId}.`;
                this.isLoading = false;
            });
            return updatedIoC;
        } catch (error) {
            runInAction(() => {
                this.error = error.message || "Failed to link IoC to APT";
                this.operationStatus = `Помилка прив'язки IoC: ${this.error}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async loadSourceNames() {
        try {
            const sources = await loadIoCsSources(); // Запит до вашого нового ендпоінту
            runInAction(() => {
                this.sourceNames = sources.sort(); // Зберігаємо та сортуємо
            });
        } catch (error) {
            console.error("Failed to load source names", error);
            // Можна обробити помилку, якщо потрібно
        }
    }

    async loadUniqueTags() {
        try {
            const uniqueTags = await loadIoCsUniqueTags(); // Запит до вашого нового ендпоінту
            runInAction(() => {
                this.uniqueTags = uniqueTags.sort(); // Зберігаємо та сортуємо
            });
        } catch (error) {
            console.error("Failed to load source names", error);
            // Можна обробити помилку, якщо потрібно
        }
    }
}

const indicatorStore = new IndicatorStore();
export default indicatorStore;