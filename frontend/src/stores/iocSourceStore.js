// src/stores/iocSourceStore.js
import { makeObservable, observable, action, runInAction, computed } from 'mobx';
import {
    getAllIoCSources,
    createIoCSource,
    updateIoCSource,
    deleteIoCSource,
    fetchIoCsFromSource,
    getIoCSourceById
} from '../api/iocSourceApi';
// Можливо, потрібен буде індикаторний стор для оновлення списку IoC після fetch
// import indicatorStore from './indicatorStore';

class IoCSourceStore {
    sources = [];
    currentSource = null; // Для форми редагування або деталей
    isLoading = false;
    error = null;
    fetchStatus = ''; // Для відображення повідомлень від fetchIoCsFromSource

    pagination = {
        count: 0,
        page: 0,
        rowsPerPage: 10,
    };

    constructor() {
        makeObservable(this, {
            sources: observable.struct,
            currentSource: observable.deep,
            isLoading: observable,
            error: observable,
            fetchStatus: observable,
            pagination: observable.deep,

            fetchSources: action,
            fetchSourceById: action,
            addSource: action,
            saveSource: action,
            removeSource: action,
            triggerFetchIoCs: action,
            clearCurrentSource: action,
            setPagination: action,

            totalSources: computed,
        });
    }

    setPagination(page, rowsPerPage) {
        this.pagination.page = page;
        this.pagination.rowsPerPage = rowsPerPage;
        this.fetchSources();
    }

    get totalSources() {
        return this.pagination.count;
    }

    clearCurrentSource() {
        this.currentSource = null;
    }

    async fetchSources() {
        this.isLoading = true;
        this.error = null;
        try {
            const skip = this.pagination.page * this.pagination.rowsPerPage;
            const limit = this.pagination.rowsPerPage;
            const data = await getAllIoCSources(skip, limit); // Припускаємо, що API повертає масив
            runInAction(() => {
                this.sources = data;
                // Якщо API повертає загальну кількість:
                // this.pagination.count = data.totalCount;
                // А поки що, для клієнтської пагінації або якщо немає totalCount:
                if (this.pagination.page === 0 && data.length < this.pagination.rowsPerPage) {
                    this.pagination.count = data.length; // Якщо це всі дані
                } else if (data.length === 0 && this.pagination.page > 0) {
                    // Якщо ми на сторінці > 0 і даних немає, можливо, потрібно перейти назад
                    // або просто показати, що даних немає
                }
                // Для коректної серверної пагінації API має повертати total
                this.isLoading = false;
            });
        } catch (error) {
            runInAction(() => {
                this.error = error.message || "Failed to fetch IoC sources";
                this.isLoading = false;
            });
        }
    }

    async fetchSourceById(sourceId) {
        this.isLoading = true;
        this.error = null;
        try {
            const data = await getIoCSourceById(sourceId);
            runInAction(() => {
                this.currentSource = data;
                this.isLoading = false;
            });
            return data;
        } catch (error) {
            runInAction(() => {
                this.error = error.message || `Failed to fetch IoC source ${sourceId}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async addSource(sourceData) {
        this.isLoading = true;
        this.error = null;
        try {
            const newSource = await createIoCSource(sourceData);
            runInAction(() => {
                this.fetchSources(); // Оновити список
                this.isLoading = false;
            });
            return newSource;
        } catch (error) {
            runInAction(() => {
                this.error = error.detail || error.message || "Failed to create IoC source";
                this.isLoading = false;
            });
            throw error;
        }
    }

    async saveSource(sourceId, sourceUpdateData) {
        this.isLoading = true;
        this.error = null;
        try {
            const updatedSource = await updateIoCSource(sourceId, sourceUpdateData);
            runInAction(() => {
                this.fetchSources(); // Оновити список
                if (this.currentSource && this.currentSource.id === sourceId) {
                    this.currentSource = updatedSource;
                }
                this.isLoading = false;
            });
            return updatedSource;
        } catch (error) {
            runInAction(() => {
                this.error = error.detail || error.message || `Failed to update IoC source ${sourceId}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async removeSource(sourceId) {
        this.isLoading = true;
        this.error = null;
        try {
            await deleteIoCSource(sourceId);
            runInAction(() => {
                this.fetchSources(); // Оновити список
                if (this.currentSource && this.currentSource.id === sourceId) {
                    this.currentSource = null;
                }
                this.isLoading = false;
            });
        } catch (error) {
            runInAction(() => {
                this.error = error.detail || error.message || `Failed to delete IoC source ${sourceId}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async triggerFetchIoCs(sourceId) {
        this.isLoading = true; // Або окремий isLoading для цієї операції
        this.error = null;
        this.fetchStatus = `Завантаження IoC для джерела ID: ${sourceId}...`;
        try {
            const result = await fetchIoCsFromSource(sourceId);
            runInAction(() => {
                this.fetchStatus = result.message || "Завантаження IoC завершено.";
                this.isLoading = false;
                // Тут можна було б оновити лічильник IoC або щось подібне,
                // або навіть запустити оновлення списку IoC в indicatorStore, якщо є зв'язок.
                // indicatorStore.fetchIoCs();
            });
            return result;
        } catch (error) {
            runInAction(() => {
                this.error = error.detail || error.message || `Failed to fetch IoCs for source ${sourceId}`;
                this.fetchStatus = `Помилка завантаження IoC: ${this.error}`;
                this.isLoading = false;
            });
            throw error;
        }
    }
}

const iocSourceStore = new IoCSourceStore();
export default iocSourceStore;