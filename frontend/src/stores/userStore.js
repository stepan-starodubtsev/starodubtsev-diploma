// frontend/src/stores/userStore.js
import { makeAutoObservable, runInAction } from 'mobx';
import { getUsers, createUser, updateUser, deleteUser } from '../api/userApi';

class UserStore {
    users = [];
    isLoading = false;
    error = null;

    constructor() {
        makeAutoObservable(this);
    }

    async fetchUsers() {
        this.isLoading = true;
        try {
            const users = await getUsers();
            runInAction(() => {
                this.users = users;
                this.isLoading = false;
            });
        } catch (error) {
            runInAction(() => {
                this.error = 'Failed to fetch users';
                this.isLoading = false;
            });
        }
    }

    async addUser(userData) {
        this.isLoading = true;
        try {
            const newUser = await createUser(userData);
            runInAction(() => {
                this.users.push(newUser);
                this.isLoading = false;
            });
            return newUser;
        } catch (error) {
            runInAction(() => {
                this.error = 'Failed to create user';
                this.isLoading = false;
            });
            throw error;
        }
    }

    async saveUser(userId, userData) {
        this.isLoading = true;
        try {
            const updatedUser = await updateUser(userId, userData);
            runInAction(() => {
                const index = this.users.findIndex(u => u.id === userId);
                if (index !== -1) {
                    this.users[index] = updatedUser;
                }
                this.isLoading = false;
            });
            return updatedUser;
        } catch (error) {
            runInAction(() => {
                this.error = 'Failed to update user';
                this.isLoading = false;
            });
            throw error;
        }
    }

    async removeUser(userId) {
        this.isLoading = true;
        try {
            await deleteUser(userId);
            runInAction(() => {
                this.users = this.users.filter(u => u.id !== userId);
                this.isLoading = false;
            });
        } catch (error) {
            runInAction(() => {
                this.error = 'Failed to delete user';
                this.isLoading = false;
            });
        }
    }
}

const userStore = new UserStore();
export default userStore;