// src/api/aptGroupApi.js
import apiClient from './apiClient';

const APT_GROUPS_PREFIX = '/apt-groups'; // Префікс роутера з apt_groups/api.py

export const createAptGroup = async (aptData) => {
    try {
        const response = await apiClient.post(`${APT_GROUPS_PREFIX}/`, aptData);
        return response.data;
    } catch (error) {
        console.error('Error creating APT group:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getAllAptGroups = async (skip = 0, limit = 100) => {
    try {
        const response = await apiClient.get(`${APT_GROUPS_PREFIX}/`, {
            params: { skip, limit },
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching APT groups:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getAptGroupById = async (groupId) => {
    try {
        const response = await apiClient.get(`${APT_GROUPS_PREFIX}/${groupId}`);
        return response.data;
    } catch (error) {
        console.error(`Error fetching APT group ${groupId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const updateAptGroup = async (groupId, aptUpdateData) => {
    try {
        const response = await apiClient.put(`${APT_GROUPS_PREFIX}/${groupId}`, aptUpdateData);
        return response.data;
    } catch (error) {
        console.error(`Error updating APT group ${groupId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const deleteAptGroup = async (groupId) => {
    try {
        await apiClient.delete(`${APT_GROUPS_PREFIX}/${groupId}`);
        return { success: true, groupId };
    } catch (error) {
        console.error(`Error deleting APT group ${groupId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getIoCsForAptGroup = async (groupId, skip = 0, limit = 100) => {
    try {
        const response = await apiClient.get(`${APT_GROUPS_PREFIX}/${groupId}/iocs`, {
            params: { skip, limit },
        });
        return response.data; // Очікуємо List[IoCResponse]
    } catch (error) {
        console.error(`Error fetching IoCs for APT group ${groupId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};