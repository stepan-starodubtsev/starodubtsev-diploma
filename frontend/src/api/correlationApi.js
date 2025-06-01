// src/api/correlationApi.js
import apiClient from './apiClient';

const CORRELATION_PREFIX = '/correlation'; // Префікс роутера з correlation/api.py

// --- CRUD для CorrelationRule ---
export const createCorrelationRule = async (ruleData) => {
    try {
        const response = await apiClient.post(`${CORRELATION_PREFIX}/rules/`, ruleData);
        return response.data;
    } catch (error) {
        console.error('Error creating correlation rule:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getAllCorrelationRules = async (skip = 0, limit = 100, onlyEnabled = true) => {
    try {
        const response = await apiClient.get(`${CORRELATION_PREFIX}/rules/`, {
            params: { skip, limit, only_enabled: onlyEnabled },
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching correlation rules:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getCorrelationRuleById = async (ruleId) => {
    try {
        const response = await apiClient.get(`${CORRELATION_PREFIX}/rules/${ruleId}`);
        return response.data;
    } catch (error) {
        console.error(`Error fetching correlation rule ${ruleId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const updateCorrelationRule = async (ruleId, ruleUpdateData) => {
    try {
        const response = await apiClient.put(`${CORRELATION_PREFIX}/rules/${ruleId}`, ruleUpdateData);
        return response.data;
    } catch (error) {
        console.error(`Error updating correlation rule ${ruleId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const deleteCorrelationRule = async (ruleId) => {
    try {
        await apiClient.delete(`${CORRELATION_PREFIX}/rules/${ruleId}`);
        return { success: true, ruleId };
    } catch (error) {
        console.error(`Error deleting correlation rule ${ruleId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

// --- Ендпоїнт для запуску циклу кореляції ---
export const triggerCorrelationCycle = async () => {
    try {
        const response = await apiClient.post(`${CORRELATION_PREFIX}/run-cycle/`);
        return response.data; // Очікуємо {"message": "..."}
    } catch (error) {
        console.error('Error triggering correlation cycle:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

// --- CRUD для Offence (якщо потрібно керувати звідси, або створити окремий offenceApi.js) ---
// Зазвичай перегляд офенсів - це окрема сторінка/модуль.
// Але тут можна додати отримання списку для дашборду або швидкого перегляду.

export const getAllOffences = async (skip = 0, limit = 100) => {
    try {
        const response = await apiClient.get(`${CORRELATION_PREFIX}/offences/`, {
            params: { skip, limit },
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching offences:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getOffenceById = async (offenceId) => {
    try {
        const response = await apiClient.get(`${CORRELATION_PREFIX}/offences/${offenceId}`);
        return response.data;
    } catch (error) {
        console.error(`Error fetching offence ${offenceId}:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const updateOffenceStatus = async (offenceId, statusUpdateData) => {
    try {
        // Замість PUT /offences/{offence_id}/status, у нас був PUT /offences/{offence_id}
        // Якщо API очікує PUT на /offences/{offence_id}/status, то зміни шлях.
        // Поточний API в correlation/api.py очікує PUT /offences/{offence_id}/status
        const response = await apiClient.put(`${CORRELATION_PREFIX}/offences/${offenceId}/status`, statusUpdateData);
        return response.data;
    } catch (error) {
        console.error(`Error updating offence ${offenceId} status:`, error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

// Функція для завантаження дефолтних правил (якщо є такий ендпоінт)
export const loadDefaultCorrelationRules = async () => {
    try {
        const response = await apiClient.post(`${CORRELATION_PREFIX}/rules/load-defaults`);
        return response.data; // Очікуємо {"created": X, "skipped": Y}
    } catch (error) {
        console.error('Error loading default correlation rules:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getTopTriggeredIoCs = async (limit = 10, daysBack = 7) => {
    try {
        const response = await apiClient.get(`${CORRELATION_PREFIX}/dashboard/offences/top_triggered_iocs`, {
            params: { limit, days_back: daysBack },
        });
        return response.data; // Очікуємо List[TopIoCTrigger]
    } catch (error) {
        console.error('Error fetching top triggered IoCs:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getOffencesByApt = async (daysBack = 7) => {
    try {
        const response = await apiClient.get(`${CORRELATION_PREFIX}/dashboard/offences/by_apt`, {
            params: { days_back: daysBack },
        });
        return response.data; // Очікуємо List[AptOffenceSummary]
    } catch (error) {
        console.error('Error fetching offences by APT:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};

export const getOffencesSummaryBySeverity = async (daysBack = 7) => {
    try {
        const response = await apiClient.get(`${CORRELATION_PREFIX}/dashboard/offences/summary_by_severity`, {
            params: { days_back: daysBack },
        });
        return response.data; // Очікуємо Dict[str, int] (наприклад, {"low": 5, "medium": 10})
    } catch (error) {
        console.error('Error fetching offences summary by severity:', error.response?.data || error.message);
        throw error.response?.data || error;
    }
};