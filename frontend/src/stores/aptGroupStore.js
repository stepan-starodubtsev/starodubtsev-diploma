// src/stores/aptGroupStore.js
import { makeObservable, observable, action, runInAction, computed } from 'mobx';
import {
    getAllAptGroups,
    createAptGroup,
    updateAptGroup,
    deleteAptGroup,
    getAptGroupById,
    getIoCsForAptGroup
} from '../api/aptGroupApi';

class APTGroupStore {
    aptGroups = [];
    currentAptGroup = null; // Для деталей або форми редагування
    linkedIoCs = []; // IoC, пов'язані з currentAptGroup

    isLoading = false;
    isLoadingIoCs = false; // Окремий індикатор для завантаження IoC
    error = null;
    operationStatus = ''; // Для повідомлень про успіх/невдачу операцій

    pagination = {
        count: 0,
        page: 0,
        rowsPerPage: 10,
    };

    iocsPagination = { // Пагінація для списку IoC на сторінці деталей APT
        count: 0,
        page: 0,
        rowsPerPage: 5,
    };

    constructor() {
        makeObservable(this, {
            aptGroups: observable.struct,
            currentAptGroup: observable.deep,
            linkedIoCs: observable.struct,
            isLoading: observable,
            isLoadingIoCs: observable,
            error: observable,
            operationStatus: observable,
            pagination: observable.deep,
            iocsPagination: observable.deep,

            fetchAptGroups: action,
            fetchAptGroupById: action,
            addAptGroup: action,
            saveAptGroup: action,
            removeAptGroup: action,
            fetchLinkedIoCs: action,
            clearCurrentAptGroup: action,
            setPagination: action,
            setIoCsPagination: action,

            totalAptGroups: computed,
            totalLinkedIoCs: computed,
        });
    }

    setPagination(page, rowsPerPage) {
        this.pagination.page = page;
        this.pagination.rowsPerPage = rowsPerPage;
        this.fetchAptGroups();
    }

    setIoCsPagination(page, rowsPerPage) {
        this.iocsPagination.page = page;
        this.iocsPagination.rowsPerPage = rowsPerPage;
        if (this.currentAptGroup) {
            this.fetchLinkedIoCs(this.currentAptGroup.id);
        }
    }

    get totalAptGroups() {
        return this.pagination.count;
    }

    get totalLinkedIoCs() {
        return this.iocsPagination.count;
    }

    clearCurrentAptGroup() {
        this.currentAptGroup = null;
        this.linkedIoCs = [];
        this.iocsPagination.page = 0; // Скидаємо пагінацію IoC
    }

    async fetchAptGroups() {
        this.isLoading = true;
        this.error = null;
        try {
            const skip = this.pagination.page * this.pagination.rowsPerPage;
            const limit = this.pagination.rowsPerPage;
            const data = await getAllAptGroups(skip, limit);
            runInAction(() => {
                this.aptGroups = data;
                // Припускаємо, що API може повертати total count, якщо ні - потрібна інша логіка
                // this.pagination.count = data.totalCount || data.length;
                this.isLoading = false;
            });
        } catch (error) {
            runInAction(() => {
                this.error = error.message || "Failed to fetch APT groups";
                this.isLoading = false;
            });
        }
    }

    async fetchAptGroupById(groupId) {
        this.isLoading = true;
        this.error = null;
        this.clearCurrentAptGroup(); // Очищаємо перед завантаженням нового
        try {
            const data = await getAptGroupById(groupId);
            runInAction(() => {
                this.currentAptGroup = data;
                this.isLoading = false;
            });
            // Після завантаження APT групи, завантажимо пов'язані IoC
            if (data) {
                await this.fetchLinkedIoCs(groupId);
            }
            return data;
        } catch (error) {
            runInAction(() => {
                this.error = error.message || `Failed to fetch APT group ${groupId}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async addAptGroup(aptData) {
        this.isLoading = true;
        this.error = null;
        this.operationStatus = '';
        try {
            const newGroup = await createAptGroup(aptData);
            runInAction(() => {
                this.fetchAptGroups(); // Оновити список
                this.operationStatus = `APT угруповання "${newGroup.name}" успішно створено.`;
                this.isLoading = false;
            });
            return newGroup;
        } catch (error) {
            runInAction(() => {
                this.error = error.detail || error.message || "Failed to create APT group";
                this.operationStatus = `Помилка створення APT: ${this.error}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async saveAptGroup(groupId, aptUpdateData) {
        this.isLoading = true;
        this.error = null;
        this.operationStatus = '';
        try {
            const updatedGroup = await updateAptGroup(groupId, aptUpdateData);
            runInAction(() => {
                this.fetchAptGroups(); // Оновити список
                if (this.currentAptGroup && this.currentAptGroup.id === groupId) {
                    this.currentAptGroup = updatedGroup;
                }
                this.operationStatus = `APT угруповання "${updatedGroup.name}" успішно оновлено.`;
                this.isLoading = false;
            });
            return updatedGroup;
        } catch (error) {
            runInAction(() => {
                this.error = error.detail || error.message || `Failed to update APT group ${groupId}`;
                this.operationStatus = `Помилка оновлення APT: ${this.error}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async removeAptGroup(groupId) {
        this.isLoading = true;
        this.error = null;
        this.operationStatus = '';
        try {
            await deleteAptGroup(groupId);
            runInAction(() => {
                this.fetchAptGroups(); // Оновити список
                if (this.currentAptGroup && this.currentAptGroup.id === groupId) {
                    this.clearCurrentAptGroup();
                }
                this.operationStatus = `APT угруповання ID ${groupId} успішно видалено.`;
                this.isLoading = false;
            });
        } catch (error) {
            runInAction(() => {
                this.error = error.detail || error.message || `Failed to delete APT group ${groupId}`;
                this.operationStatus = `Помилка видалення APT: ${this.error}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async fetchLinkedIoCs(groupId) {
        this.isLoadingIoCs = true;
        this.error = null; // Можна мати окрему помилку для IoC
        try {
            const skip = this.iocsPagination.page * this.iocsPagination.rowsPerPage;
            const limit = this.iocsPagination.rowsPerPage;
            const data = await getIoCsForAptGroup(groupId, skip, limit); // Припускаємо, що API повертає масив IoC
            runInAction(() => {
                this.linkedIoCs = data;
                // Якщо API повертає totalCount для IoC, оновлюємо this.iocsPagination.count
                // this.iocsPagination.count = data.totalCount || data.length;
                this.isLoadingIoCs = false;
            });
        } catch (error) {
            runInAction(() => {
                this.error = error.message || `Failed to fetch IoCs for APT group ${groupId}`;
                this.isLoadingIoCs = false;
            });
        }
    }
}

const aptGroupStore = new APTGroupStore();
export default aptGroupStore;