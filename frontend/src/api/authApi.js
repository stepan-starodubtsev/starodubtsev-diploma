// frontend/src/api/authApi.js
import apiClient from './apiClient';

export const login = async (username, password) => {
    // FastAPI OAuth2PasswordRequestForm очікує дані у форматі form-data
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    const response = await apiClient.post('/auth/token', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
};

export const getMe = async () => {
    const response = await apiClient.get('/auth/users/me/');
    return response.data;
}