// frontend/src/api/apiClient.js
import axios from 'axios';

const apiClient = axios.create({
    baseURL: 'http://localhost:8000', // URL вашого бекенду
});

// Додаємо interceptor для обробки помилок 401 Unauthorized
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            // Якщо сервер повернув 401, це означає, що токен недійсний.
            // Викидаємо користувача з системи.
            // Прямий виклик authStore.logout() тут може створити циклічну залежність.
            // Краще повідомити додаток про це і обробити в іншому місці.
            // Наприклад, можна видалити токен і перезавантажити сторінку.
            localStorage.removeItem('token');
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);


export default apiClient;