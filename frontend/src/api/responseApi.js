// src/api/responseApi.js
import apiClient from './apiClient';

const RESPONSE_PREFIX = '/response-management'; // Префікс роутера з response/api.py

// --- CRUD для Response Actions ---
export const createResponseAction = async (actionData) => {
    try {
        const response = await apiClient.post(`${RESPONSE_PREFIX}/actions/`, actionData);
        return response.data;
    } catch (error) {
        console.error('Error creating response action:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getAllResponseActions = async (skip = 0, limit = 100) => {
    try {
        const response = await apiClient.get(`${RESPONSE_PREFIX}/actions/`, {
            params: { skip, limit },
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching response actions:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getResponseActionById = async (actionId) => {
    try {
        const response = await apiClient.get(`${RESPONSE_PREFIX}/actions/${actionId}`);
        return response.data;
    } catch (error) {
        console.error(`Error fetching response action ${actionId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const updateResponseAction = async (actionId, actionUpdateData) => {
    try {
        const response = await apiClient.put(`${RESPONSE_PREFIX}/actions/${actionId}`, actionUpdateData);
        return response.data;
    } catch (error) {
        console.error(`Error updating response action ${actionId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const deleteResponseAction = async (actionId) => {
    try {
        await apiClient.delete(`${RESPONSE_PREFIX}/actions/${actionId}`);
        return { success: true, actionId };
    } catch (error) {
        console.error(`Error deleting response action ${actionId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

// --- CRUD для Response Pipelines ---
export const createResponsePipeline = async (pipelineData) => {
    try {
        const response = await apiClient.post(`${RESPONSE_PREFIX}/pipelines/`, pipelineData);
        return response.data;
    } catch (error) {
        console.error('Error creating response pipeline:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getAllResponsePipelines = async (skip = 0, limit = 100) => {
    try {
        const response = await apiClient.get(`${RESPONSE_PREFIX}/pipelines/`, {
            params: { skip, limit },
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching response pipelines:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getResponsePipelineById = async (pipelineId) => {
    try {
        const response = await apiClient.get(`${RESPONSE_PREFIX}/pipelines/${pipelineId}`);
        return response.data;
    } catch (error) {
        console.error(`Error fetching response pipeline ${pipelineId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const updateResponsePipeline = async (pipelineId, pipelineUpdateData) => {
    try {
        const response = await apiClient.put(`${RESPONSE_PREFIX}/pipelines/${pipelineId}`, pipelineUpdateData);
        return response.data;
    } catch (error) {
        console.error(`Error updating response pipeline ${pipelineId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const deleteResponsePipeline = async (pipelineId) => {
    try {
        await apiClient.delete(`${RESPONSE_PREFIX}/pipelines/${pipelineId}`);
        return { success: true, pipelineId };
    } catch (error) {
        console.error(`Error deleting response pipeline ${pipelineId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

// --- Ендпоїнт для тестового запуску реагування на офенс ---
export const triggerExecuteResponseForOffence = async (offenceId) => {
    try {
        const response = await apiClient.post(`${RESPONSE_PREFIX}/execute-for-offence/`, { offence_id: offenceId });
        return response.data; // Очікуємо {"message": "..."}
    } catch (error) {
        console.error(`Error triggering response for offence ${offenceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};