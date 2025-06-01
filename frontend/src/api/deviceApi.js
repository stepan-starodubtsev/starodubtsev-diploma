// src/api/deviceApi.js
import apiClient from './apiClient';

const DEVICES_PREFIX = '/devices'; // Префікс роутера з device_interaction/api.py

// CRUD для пристроїв
export const createDevice = async (deviceData) => {
    try {
        const response = await apiClient.post(`${DEVICES_PREFIX}/`, deviceData);
        return response.data;
    } catch (error) {
        console.error('Error creating device:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getAllDevices = async (skip = 0, limit = 100) => {
    try {
        const response = await apiClient.get(`${DEVICES_PREFIX}/`, {
            params: { skip, limit },
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching devices:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getDeviceById = async (deviceId) => {
    try {
        const response = await apiClient.get(`${DEVICES_PREFIX}/${deviceId}`);
        return response.data;
    } catch (error) {
        console.error(`Error fetching device ${deviceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const updateDevice = async (deviceId, deviceUpdateData) => {
    try {
        const response = await apiClient.put(`${DEVICES_PREFIX}/${deviceId}`, deviceUpdateData);
        return response.data;
    } catch (error) {
        console.error(`Error updating device ${deviceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const deleteDevice = async (deviceId) => {
    try {
        await apiClient.delete(`${DEVICES_PREFIX}/${deviceId}`);
        // DELETE зазвичай повертає 204 No Content, тому response.data може не бути
        return { success: true, deviceId };
    } catch (error) {
        console.error(`Error deleting device ${deviceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

// Операції з пристроями
export const getDeviceStatus = async (deviceId) => {
    try {
        const response = await apiClient.get(`${DEVICES_PREFIX}/${deviceId}/status`);
        return response.data;
    } catch (error) {
        console.error(`Error fetching status for device ${deviceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const configureDeviceSyslog = async (deviceId, syslogConfigData) => {
    try {
        const response = await apiClient.post(`${DEVICES_PREFIX}/${deviceId}/configure-syslog`, syslogConfigData);
        return response.data; // Очікуємо {"message": "...", "success": true/false}
    } catch (error) {
        console.error(`Error configuring syslog for device ${deviceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const configureDeviceNetflow = async (deviceId, netflowConfigData) => {
    try {
        const response = await apiClient.post(`${DEVICES_PREFIX}/${deviceId}/configure-netflow`, netflowConfigData);
        return response.data;
    } catch (error) {
        console.error(`Error configuring netflow for device ${deviceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getDeviceFirewallRules = async (deviceId, chain = null) => {
    try {
        const params = {};
        if (chain) {
            params.chain = chain;
        }
        const response = await apiClient.get(`${DEVICES_PREFIX}/${deviceId}/firewall-rules`, { params });
        return response.data; // Очікуємо List[Dict[str, Any]]
    } catch (error) {
        console.error(`Error fetching firewall rules for device ${deviceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const blockIpOnDevice = async (deviceId, blockIpPayload) => {
    try {
        const response = await apiClient.post(`${DEVICES_PREFIX}/${deviceId}/block-ip`, blockIpPayload);
        return response.data;
    } catch (error) {
        console.error(`Error blocking IP on device ${deviceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const unblockIpOnDevice = async (deviceId, unblockIpPayload) => {
    try {
        const response = await apiClient.post(`${DEVICES_PREFIX}/${deviceId}/unblock-ip`, unblockIpPayload);
        return response.data;
    } catch (error) {
        console.error(`Error unblocking IP on device ${deviceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};