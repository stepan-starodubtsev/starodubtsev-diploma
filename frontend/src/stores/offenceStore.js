// src/stores/offenceStore.js
import { makeObservable, observable, action, runInAction, computed } from 'mobx';
import {
    getAllOffences,
    getOffenceById,
    updateOffenceStatus
} from '../api/correlationApi'; // Припускаємо, що функції API для офенсів там

class OffenceStore {
    offences = [];
    currentOffence = null; // Для деталей

    isLoading = false;
    error = null;
    operationStatus = ''; // Для повідомлень про успіх/невдачу операцій

    pagination = {
        count: 0, // Загальна кількість (якщо API повертає)
        page: 0,
        rowsPerPage: 10,
        // Можна додати фільтри для статусу, серйозності тощо.
        filterStatus: null,
        filterSeverity: null,
    };

    constructor() {
        makeObservable(this, {
            offences: observable.struct,
            currentOffence: observable.deep,
            isLoading: observable,
            error: observable,
            operationStatus: observable,
            pagination: observable.deep,

            fetchOffences: action,
            fetchOffenceById: action,
            updateStatus: action, // Для оновлення статусу та нотаток
            clearCurrentOffence: action,
            setPagination: action,
            setFilters: action, // Для встановлення фільтрів

            totalOffences: computed,
        });
    }

    setPagination(page, rowsPerPage) {
        this.pagination.page = page;
        this.pagination.rowsPerPage = rowsPerPage;
        this.fetchOffences();
    }

    setFilters(status, severity) {
        this.pagination.filterStatus = status;
        this.pagination.filterSeverity = severity;
        this.pagination.page = 0; // Скидаємо на першу сторінку при фільтрації
        this.fetchOffences();
    }

    get totalOffences() {
        return this.pagination.count;
    }

    clearCurrentOffence() {
        this.currentOffence = null;
    }

    async fetchOffences() {
        this.isLoading = true;
        this.error = null;
        try {
            const skip = this.pagination.page * this.pagination.rowsPerPage;
            const limit = this.pagination.rowsPerPage;
            // TODO: Додати передачу фільтрів (status, severity) в API функцію getAllOffences,
            // якщо бекенд це підтримує.
            const data = await getAllOffences(skip, limit /*, this.pagination.filterStatus, this.pagination.filterSeverity */);
            runInAction(() => {
                this.offences = data;
                // this.pagination.count = data.totalCount; // Якщо API повертає
                this.isLoading = false;
            });
        } catch (error) {
            runInAction(() => {
                this.error = error.message || "Failed to fetch offences";
                this.isLoading = false;
            });
        }
    }

    async fetchOffenceById(offenceId) {
        this.isLoading = true;
        this.error = null;
        this.currentOffence = null;
        try {
            const data = await getOffenceById(offenceId);
            runInAction(() => {
                this.currentOffence = data;
                this.isLoading = false;
            });
            return data;
        } catch (error) {
            runInAction(() => {
                this.error = error.message || `Failed to fetch offence ${offenceId}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async updateStatus(offenceId, newStatus, notes = null, newSeverity = null) {
        this.isLoading = true; // Можна мати окремий isLoading для оновлення
        this.error = null;
        this.operationStatus = '';
        try {
            const payload = { status: newStatus };
            if (notes !== null) payload.notes = notes;
            if (newSeverity !== null) payload.severity = newSeverity; // Якщо API дозволяє оновлювати серйозність

            const updatedOffence = await updateOffenceStatus(offenceId, payload);
            runInAction(() => {
                // Оновлюємо офенс у списку
                const index = this.offences.findIndex(off => off.id === offenceId);
                if (index !== -1) {
                    this.offences[index] = updatedOffence;
                }
                if (this.currentOffence && this.currentOffence.id === offenceId) {
                    this.currentOffence = updatedOffence;
                }
                this.operationStatus = `Статус офенса ID ${offenceId} успішно оновлено до '${newStatus}'.`;
                this.isLoading = false;
            });
            return updatedOffence;
        } catch (error) {
            runInAction(() => {
                this.error = error.detail || error.message || `Failed to update offence ${offenceId} status`;
                this.operationStatus = `Помилка оновлення статусу офенса: ${this.error}`;
                this.isLoading = false;
            });
            throw error;
        }
    }
}

const offenceStore = new OffenceStore();
export default offenceStore;