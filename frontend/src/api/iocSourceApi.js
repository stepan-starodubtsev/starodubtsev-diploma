// src/api/iocSourceApi.js
import apiClient from './apiClient';

const IOC_SOURCES_PREFIX = '/ioc-sources'; // Збігається з префіксом роутера на бекенді

export const createIoCSource = async (sourceData) => {
    try {
        const response = await apiClient.post(`${IOC_SOURCES_PREFIX}/`, sourceData);
        return response.data;
    } catch (error) {
        console.error('Error creating IoC source:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getAllIoCSources = async (skip = 0, limit = 100) => {
    try {
        const response = await apiClient.get(`${IOC_SOURCES_PREFIX}/`, {
            params: { skip, limit },
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching IoC sources:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getIoCSourceById = async (sourceId) => {
    try {
        const response = await apiClient.get(`${IOC_SOURCES_PREFIX}/${sourceId}`);
        return response.data;
    } catch (error) {
        console.error(`Error fetching IoC source ${sourceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const updateIoCSource = async (sourceId, sourceUpdateData) => {
    try {
        const response = await apiClient.put(`${IOC_SOURCES_PREFIX}/${sourceId}`, sourceUpdateData);
        return response.data;
    } catch (error) {
        console.error(`Error updating IoC source ${sourceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const deleteIoCSource = async (sourceId) => {
    try {
        await apiClient.delete(`${IOC_SOURCES_PREFIX}/${sourceId}`);
        return { success: true, sourceId };
    } catch (error) {
        console.error(`Error deleting IoC source ${sourceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const fetchIoCsFromSource = async (sourceId) => {
    try {
        const response = await apiClient.post(`${IOC_SOURCES_PREFIX}/${source_id}/fetch-iocs`);
        return response.data; // Очікуємо {"message": "...", "added_iocs": X, "failed_iocs": Y, "status": "success/error"}
    } catch (error) {
        console.error(`Error fetching IoCs for source ${sourceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};