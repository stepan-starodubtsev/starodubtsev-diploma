// frontend/src/api/userApi.js
import apiClient from './apiClient';

export const getUsers = async () => {
    const response = await apiClient.get('/users/');
    return response.data;
};

export const createUser = async (userData) => {
    const response = await apiClient.post('/users/', userData);
    return response.data;
};

export const updateUser = async (userId, userData) => {
    const response = await apiClient.put(`/users/${userId}`, userData);
    return response.data;
};

export const deleteUser = async (userId) => {
    const response = await apiClient.delete(`/users/${userId}`);
    return response.data;
};