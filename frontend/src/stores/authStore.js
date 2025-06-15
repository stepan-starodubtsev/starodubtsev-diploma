// frontend/src/stores/authStore.js
import { makeAutoObservable, runInAction } from 'mobx';
import { jwtDecode } from 'jwt-decode';
import apiClient from '../api/apiClient';
import { login as apiLogin } from '../api/authApi'; // Створимо цей файл далі

class AuthStore {
    token = localStorage.getItem('token') || null;
    user = null; // { username: 'admin', role: 'admin' }
    isLoading = false;
    error = null;

    constructor() {
        makeAutoObservable(this);
        this.loadUserFromToken();
    }

    get isAuthenticated() {
        return !!this.token;
    }

    get isAdmin() {
        return this.user?.role === 'admin';
    }

    loadUserFromToken() {
        if (this.token) {
            try {
                const decoded = jwtDecode(this.token);
                if (decoded.exp * 1000 > Date.now()) {
                    this.user = { username: decoded.sub, role: decoded.role };
                    apiClient.defaults.headers.common['Authorization'] = `Bearer ${this.token}`;
                } else {
                    this.logout(); // Токен прострочено
                }
            } catch (error) {
                console.error("Invalid token:", error);
                this.logout();
            }
        }
    }

    async login(username, password) {
        this.isLoading = true;
        this.error = null;
        try {
            const response = await apiLogin(username, password);
            const { access_token } = response;
            runInAction(() => {
                this.token = access_token;
                localStorage.setItem('token', access_token);
                this.loadUserFromToken();
                this.isLoading = false;
            });
        } catch (err) {
            runInAction(() => {
                const errorDetail = err.response?.data?.detail || 'Login failed. Please check your credentials.';
                this.error = errorDetail;
                this.isLoading = false;
            });
            throw err;
        }
    }

    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('token');
        delete apiClient.defaults.headers.common['Authorization'];
    }
}

const authStore = new AuthStore();
export default authStore;