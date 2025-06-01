// src/api/apiClient.js
import axios from 'axios';

// Базовий URL вашого API. Краще винести в .env файл
// Наприклад, REACT_APP_API_BASE_URL=http://localhost:8000/api/v1 (якщо є префікс /api/v1)
// Або REACT_APP_API_BASE_URL=http://localhost:8000 (якщо префікси в роутерах)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
        // Тут можна буде додати заголовки для автентифікації, наприклад:
        // 'Authorization': `Bearer ${token}`
    },
});

// (Опціонально) Інтерцептори для обробки відповідей або помилок глобально
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        // Тут можна обробляти помилки централізовано
        // Наприклад, якщо помилка 401 (неавторизований), перенаправляти на логін
        console.error('API Error:', error.response || error.message);
        return Promise.reject(error);
    }
);

export default apiClient;