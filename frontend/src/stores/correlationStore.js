// src/stores/correlationStore.js
import { makeObservable, observable, action, runInAction, computed } from 'mobx';
import {
    getAllCorrelationRules,
    createCorrelationRule,
    updateCorrelationRule,
    deleteCorrelationRule,
    getCorrelationRuleById,
    triggerCorrelationCycle,
    loadDefaultCorrelationRules,
    // Для офенсів, якщо керуємо ними тут
    getAllOffences,
    getOffenceById,
    updateOffenceStatus
} from '../api/correlationApi';

class CorrelationRuleStore {
    rules = [];
    currentRule = null;
    isLoading = false;
    error = null;
    operationStatus = ''; // Для повідомлень про успіх/невдачу

    pagination = { count: 0, page: 0, rowsPerPage: 10 };

    // Стан для офенсів (якщо ця сторінка також їх відображає або керує)
    offences = [];
    currentOffence = null;
    isLoadingOffences = false;
    offencesPagination = { count: 0, page: 0, rowsPerPage: 10 };


    constructor() {
        makeObservable(this, {
            rules: observable.struct,
            currentRule: observable.deep,
            isLoading: observable,
            error: observable,
            operationStatus: observable,
            pagination: observable.deep,
            offences: observable.struct,
            currentOffence: observable.deep,
            isLoadingOffences: observable,
            offencesPagination: observable.deep,

            fetchRules: action,
            fetchRuleById: action,
            addRule: action,
            saveRule: action,
            removeRule: action,
            runCorrelationCycle: action,
            runLoadDefaultRules: action,
            clearCurrentRule: action,
            setPagination: action,

            fetchOffences: action,
            fetchOffenceById: action,
            updateOffence: action,
            setOffencesPagination: action,
            clearCurrentOffence: action,

            totalRules: computed,
            totalOffences: computed,
        });
    }

    // --- Pagination for Rules ---
    setPagination(page, rowsPerPage) {
        this.pagination.page = page;
        this.pagination.rowsPerPage = rowsPerPage;
        this.fetchRules();
    }
    get totalRules() { return this.pagination.count; }
    clearCurrentRule() { this.currentRule = null; }

    // --- Pagination for Offences ---
    setOffencesPagination(page, rowsPerPage) {
        this.offencesPagination.page = page;
        this.offencesPagination.rowsPerPage = rowsPerPage;
        this.fetchOffences();
    }
    get totalOffences() { return this.offencesPagination.count; }
    clearCurrentOffence() { this.currentOffence = null; }


    // --- Actions for Correlation Rules ---
    async fetchRules(onlyEnabled = true) {
        this.isLoading = true; this.error = null;
        try {
            const skip = this.pagination.page * this.pagination.rowsPerPage;
            const limit = this.pagination.rowsPerPage;
            const data = await getAllCorrelationRules(skip, limit, onlyEnabled);
            runInAction(() => {
                this.rules = data;
                // this.pagination.count = data.totalCount; // Якщо API повертає
                this.isLoading = false;
            });
        } catch (error) { runInAction(() => { this.error = error.message || "Failed to fetch rules"; this.isLoading = false; }); }
    }

    async fetchRuleById(ruleId) {
        this.isLoading = true; this.error = null; this.currentRule = null;
        try {
            const data = await getCorrelationRuleById(ruleId);
            runInAction(() => { this.currentRule = data; this.isLoading = false; });
            return data;
        } catch (error) { runInAction(() => { this.error = error.message || `Failed to fetch rule ${ruleId}`; this.isLoading = false; }); throw error;}
    }

    async addRule(ruleData) {
        this.isLoading = true; this.error = null; this.operationStatus = '';
        try {
            const newRule = await createCorrelationRule(ruleData);
            runInAction(() => { this.fetchRules(); this.operationStatus = `Правило "${newRule.name}" успішно створено.`; this.isLoading = false; });
            return newRule;
        } catch (error) { runInAction(() => { this.error = error.detail || error.message || "Failed to create rule"; this.operationStatus = `Помилка створення правила: ${this.error}`; this.isLoading = false; }); throw error; }
    }

    async saveRule(ruleId, ruleUpdateData) {
        this.isLoading = true; this.error = null; this.operationStatus = '';
        try {
            const updatedRule = await updateCorrelationRule(ruleId, ruleUpdateData);
            runInAction(() => {
                this.fetchRules();
                if (this.currentRule && this.currentRule.id === ruleId) this.currentRule = updatedRule;
                this.operationStatus = `Правило "${updatedRule.name}" успішно оновлено.`;
                this.isLoading = false;
            });
            return updatedRule;
        } catch (error) { runInAction(() => { this.error = error.detail || error.message || `Failed to update rule ${ruleId}`; this.operationStatus = `Помилка оновлення правила: ${this.error}`; this.isLoading = false; }); throw error;}
    }

    async removeRule(ruleId) {
        this.isLoading = true; this.error = null; this.operationStatus = '';
        try {
            await deleteCorrelationRule(ruleId);
            runInAction(() => {
                this.fetchRules();
                if (this.currentRule && this.currentRule.id === ruleId) this.currentRule = null;
                this.operationStatus = `Правило ID ${ruleId} успішно видалено.`;
                this.isLoading = false;
            });
        } catch (error) { runInAction(() => { this.error = error.detail || error.message || `Failed to delete rule ${ruleId}`; this.operationStatus = `Помилка видалення правила: ${this.error}`; this.isLoading = false; }); throw error;}
    }

    async runCorrelationCycle() {
        this.isLoading = true; // Можна мати окремий isLoading для циклу
        this.error = null; this.operationStatus = 'Запуск циклу кореляції...';
        try {
            const result = await triggerCorrelationCycle();
            runInAction(() => {
                this.operationStatus = result.message || "Цикл кореляції завершено.";
                this.isLoading = false;
                this.fetchOffences(); // Оновити список офенсів після циклу
            });
            return result;
        } catch (error) {
            runInAction(() => {
                this.error = error.message || "Failed to trigger correlation cycle";
                this.operationStatus = `Помилка запуску циклу кореляції: ${this.error}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    async runLoadDefaultRules() {
        this.isLoading = true; this.error = null; this.operationStatus = 'Завантаження дефолтних правил...';
        try {
            const result = await loadDefaultCorrelationRules();
            runInAction(() => {
                this.operationStatus = `Дефолтні правила оброблено. Створено: ${result.created}, Пропущено: ${result.skipped}`;
                this.isLoading = false;
                this.fetchRules(); // Оновити список правил
            });
            return result;
        } catch (error) {
            runInAction(() => {
                this.error = error.message || "Failed to load default rules";
                this.operationStatus = `Помилка завантаження дефолтних правил: ${this.error}`;
                this.isLoading = false;
            });
            throw error;
        }
    }

    // --- Actions for Offences ---
    async fetchOffences() {
        this.isLoadingOffences = true; this.error = null;
        try {
            const skip = this.offencesPagination.page * this.offencesPagination.rowsPerPage;
            const limit = this.offencesPagination.rowsPerPage;
            const data = await getAllOffences(skip, limit);
            runInAction(() => {
                this.offences = data;
                // this.offencesPagination.count = data.totalCount; // Якщо API повертає
                this.isLoadingOffences = false;
            });
        } catch (error) { runInAction(() => { this.error = error.message || "Failed to fetch offences"; this.isLoadingOffences = false; }); }
    }

    async fetchOffenceById(offenceId) {
        this.isLoadingOffences = true; this.error = null; this.currentOffence = null;
        try {
            const data = await getOffenceById(offenceId);
            runInAction(() => { this.currentOffence = data; this.isLoadingOffences = false; });
            return data;
        } catch (error) { runInAction(() => { this.error = error.message || `Failed to fetch offence ${offenceId}`; this.isLoadingOffences = false; }); throw error; }
    }

    async updateOffence(offenceId, statusUpdateData) {
        this.isLoadingOffences = true; this.error = null; this.operationStatus = '';
        try {
            const updatedOffence = await updateOffenceStatus(offenceId, statusUpdateData);
            runInAction(() => {
                this.fetchOffences(); // Оновити список
                if (this.currentOffence && this.currentOffence.id === offenceId) this.currentOffence = updatedOffence;
                this.operationStatus = `Статус офенса ID ${offenceId} успішно оновлено.`;
                this.isLoadingOffences = false;
            });
            return updatedOffence;
        } catch (error) { runInAction(() => { this.error = error.detail || error.message || `Failed to update offence ${offenceId}`; this.operationStatus = `Помилка оновлення статусу офенса: ${this.error}`; this.isLoadingOffences = false; }); throw error; }
    }
}

const correlationStore = new CorrelationRuleStore();
export default correlationStore;