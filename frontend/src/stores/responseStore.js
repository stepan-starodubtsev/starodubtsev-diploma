// src/stores/responseStore.js
import { makeObservable, observable, action, runInAction, computed } from 'mobx';
import {
    getAllResponseActions, createResponseAction, updateResponseAction, deleteResponseAction, getResponseActionById,
    getAllResponsePipelines, createResponsePipeline, updateResponsePipeline, deleteResponsePipeline, getResponsePipelineById,
    triggerExecuteResponseForOffence
} from '../api/responseApi';
// import offenceStore from './offenceStore'; // Якщо потрібен список офенсів для вибору

class ResponseStore {
    actions = [];
    currentAction = null;
    pipelines = [];
    currentPipeline = null;

    isLoadingActions = false;
    isLoadingPipelines = false;
    error = null;
    operationStatus = '';

    // Пагінація може бути окремою для дій та пайплайнів
    actionsPagination = { count: 0, page: 0, rowsPerPage: 10 };
    pipelinesPagination = { count: 0, page: 0, rowsPerPage: 10 };

    constructor() {
        makeObservable(this, {
            actions: observable.struct,
            currentAction: observable.deep,
            pipelines: observable.struct,
            currentPipeline: observable.deep,
            isLoadingActions: observable,
            isLoadingPipelines: observable,
            error: observable,
            operationStatus: observable,
            actionsPagination: observable.deep,
            pipelinesPagination: observable.deep,

            fetchActions: action,
            fetchActionById: action,
            addAction: action,
            saveAction: action,
            removeAction: action,
            clearCurrentAction: action,
            setActionsPagination: action,

            fetchPipelines: action,
            fetchPipelineById: action,
            addPipeline: action,
            savePipeline: action,
            removePipeline: action,
            clearCurrentPipeline: action,
            setPipelinesPagination: action,

            runResponseForOffence: action,

            totalActions: computed,
            totalPipelines: computed,
        });
    }

    // --- Pagination ---
    setActionsPagination(page, rowsPerPage) {
        this.actionsPagination.page = page;
        this.actionsPagination.rowsPerPage = rowsPerPage;
        this.fetchActions();
    }
    get totalActions() { return this.actionsPagination.count; }

    setPipelinesPagination(page, rowsPerPage) {
        this.pipelinesPagination.page = page;
        this.pipelinesPagination.rowsPerPage = rowsPerPage;
        this.fetchPipelines();
    }
    get totalPipelines() { return this.pipelinesPagination.count; }

    clearCurrentAction() { this.currentAction = null; }
    clearCurrentPipeline() { this.currentPipeline = null; }

    // --- Actions for Response Actions ---
    async fetchActions() {
        this.isLoadingActions = true; this.error = null;
        try {
            const skip = this.actionsPagination.page * this.actionsPagination.rowsPerPage;
            const data = await getAllResponseActions(skip, this.actionsPagination.rowsPerPage);
            runInAction(() => { this.actions = data; /* this.actionsPagination.count = data.totalCount; */ this.isLoadingActions = false; });
        } catch (error) { runInAction(() => { this.error = error.message || "Failed to fetch actions"; this.isLoadingActions = false; }); }
    }

    async fetchActionById(id) { /* ... реалізація за аналогією ... */ }
    async addAction(actionData) {
        this.isLoadingActions = true; this.error = null; this.operationStatus = '';
        try {
            const newAction = await createResponseAction(actionData);
            runInAction(() => { this.fetchActions(); this.operationStatus = `Дію "${newAction.name}" створено.`; this.isLoadingActions = false; });
            return newAction;
        } catch (error) { runInAction(() => { this.error = error.detail || error.message; this.operationStatus = `Помилка: ${this.error}`; this.isLoadingActions = false; }); throw error; }
    }
    async saveAction(id, data) { /* ... реалізація ... */ }
    async removeAction(id) { /* ... реалізація ... */ }

    // --- Actions for Response Pipelines ---
    async fetchPipelines() {
        this.isLoadingPipelines = true; this.error = null;
        try {
            const skip = this.pipelinesPagination.page * this.pipelinesPagination.rowsPerPage;
            const data = await getAllResponsePipelines(skip, this.pipelinesPagination.rowsPerPage);
            runInAction(() => { this.pipelines = data; /* this.pipelinesPagination.count = data.totalCount; */ this.isLoadingPipelines = false; });
        } catch (error) { runInAction(() => { this.error = error.message || "Failed to fetch pipelines"; this.isLoadingPipelines = false; }); }
    }

    async fetchPipelineById(id) { /* ... реалізація ... */ }
    async addPipeline(pipelineData) {
        this.isLoadingPipelines = true; this.error = null; this.operationStatus = '';
        try {
            const newPipeline = await createResponsePipeline(pipelineData);
            runInAction(() => { this.fetchPipelines(); this.operationStatus = `Пайплайн "${newPipeline.name}" створено.`; this.isLoadingPipelines = false; });
            return newPipeline;
        } catch (error) { runInAction(() => { this.error = error.detail || error.message; this.operationStatus = `Помилка: ${this.error}`; this.isLoadingPipelines = false; }); throw error; }
    }
    async savePipeline(id, data) { /* ... реалізація ... */ }
    async removePipeline(id) { /* ... реалізація ... */ }

    // --- Trigger Response ---
    async runResponseForOffence(offenceId) {
        this.isLoadingPipelines = true; // Або окремий isLoading для цієї операції
        this.error = null; this.operationStatus = `Запуск реагування для офенса ID: ${offenceId}...`;
        try {
            const result = await triggerExecuteResponseForOffence(offenceId);
            runInAction(() => {
                this.operationStatus = result.message || "Операцію реагування запущено.";
                this.isLoadingPipelines = false;
            });
            return result;
        } catch (error) {
            runInAction(() => {
                this.error = error.message || "Failed to trigger response for offence";
                this.operationStatus = `Помилка запуску реагування: ${this.error}`;
                this.isLoadingPipelines = false;
            });
            throw error;
        }
    }
}

const responseStore = new ResponseStore();
export default responseStore;