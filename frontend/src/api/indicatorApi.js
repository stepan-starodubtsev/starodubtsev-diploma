// src/api/indicatorApi.js
import apiClient from './apiClient';

const IOC_PREFIX = '/iocs'; // Префікс з indicators/api.py

export const addManualIoC = async (iocCreateData) => {
    try {
        const response = await apiClient.post(`${IOC_PREFIX}/`, iocCreateData);
        return response.data;
    } catch (error) {
        throw error.response?.data || error;
    }
};

export const getAllIoCs = async (skip = 0, limit = 100) => {
    try {
        const response = await apiClient.get(`${IOC_PREFIX}/list-all/`, { // Використовуємо /list-all/
            params: { skip, limit },
        });
        return response.data;
    } catch (error) {
        throw error.response?.data || error;
    }
};

export const getIoCsCreatedToday = async (skip = 0, limit = 100) => {
    try {
        const response = await apiClient.get(`${IOC_PREFIX}/today/`, {
            params: { skip, limit },
        });
        return response.data;
    } catch (error) {
        throw error.response?.data || error;
    }
};

export const searchIoCs = async (value, iocType = null) => {
    try {
        const params = { value };
        if (iocType) {
            params.ioc_type = iocType;
        }
        const response = await apiClient.get(`${IOC_PREFIX}/search/`, { params });
        return response.data;
    } catch (error) {
        throw error.response?.data || error;
    }
};

export const getIoCById = async (iocEsId) => { // Новий метод
    try {
        const response = await apiClient.get(`${IOC_PREFIX}/${iocEsId}`);
        return response.data;
    } catch (error) {
        throw error.response?.data || error;
    }
};

export const updateIoC = async (iocEsId, iocUpdateData) => { // Новий метод
    try {
        const response = await apiClient.put(`${IOC_PREFIX}/${iocEsId}`, iocUpdateData);
        return response.data;
    } catch (error) {
        throw error.response?.data || error;
    }
};

export const deleteIoC = async (iocEsId) => { // Новий метод
    try {
        await apiClient.delete(`${IOC_PREFIX}/${iocEsId}`);
        return { success: true, iocEsId };
    } catch (error) {
        throw error.response?.data || error;
    }
};

export const linkIoCToApt = async (iocEsId, aptGroupId) => {
    try {
        const response = await apiClient.post(`${IOC_PREFIX}/${iocEsId}/link-apt/${aptGroupId}`);
        return response.data;
    } catch (error) {
        throw error.response?.data || error;
    }
};

// Можна додати unlinkIoCFromApt, якщо є такий ендпоінт
// export const unlinkIoCToApt = async (iocEsId, aptGroupId) => { ... };