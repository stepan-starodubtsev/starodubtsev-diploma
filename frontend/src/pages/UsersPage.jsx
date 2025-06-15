import React, { useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Box, Button, Typography, CircularProgress, Alert } from '@mui/material';
import userStore from '../stores/userStore';
import UserTable from '../components/users/UserTable';
import UserFormModal from '../components/users/UserFormModal';

const UsersPage = observer(() => {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingUser, setEditingUser] = useState(null);

    useEffect(() => {
        userStore.fetchUsers();
    }, []);

    const handleOpenModal = (user = null) => {
        setEditingUser(user);
        setIsModalOpen(true);
    };

    const handleCloseModal = () => {
        setEditingUser(null);
        setIsModalOpen(false);
    };

    const handleSaveUser = async (userData, userId) => {
        try {
            if (userId) {
                await userStore.saveUser(userId, userData);
            } else {
                await userStore.addUser(userData);
            }
            handleCloseModal();
        } catch (error) {
            console.error("Failed to save user:", error);
            // Тут можна показати помилку користувачу
        }
    };

    const handleDeleteUser = async (userId) => {
        if (window.confirm('Ви впевнені, що хочете видалити цього користувача?')) {
            await userStore.removeUser(userId);
        }
    };

    return (
        <Box sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h4" component="h1">
                    Керування користувачами
                </Typography>
                <Button variant="contained" onClick={() => handleOpenModal()}>
                    Створити користувача
                </Button>
            </Box>

            {userStore.isLoading && <CircularProgress />}
            {userStore.error && <Alert severity="error">{userStore.error}</Alert>}

            {!userStore.isLoading && !userStore.error && (
                <UserTable
                    users={userStore.users}
                    onEdit={handleOpenModal}
                    onDelete={handleDeleteUser}
                />
            )}

            <UserFormModal
                open={isModalOpen}
                onClose={handleCloseModal}
                onSave={handleSaveUser}
                user={editingUser}
            />
        </Box>
    );
});

export default UsersPage;