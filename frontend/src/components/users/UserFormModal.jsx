import React, { useState, useEffect } from 'react';
import {
    Dialog, DialogActions, DialogContent, DialogTitle, Button, TextField,
    FormControl, InputLabel, Select, MenuItem, Box
} from '@mui/material';

const UserFormModal = ({ open, onClose, onSave, user }) => {
    const [formData, setFormData] = useState({
        username: '',
        full_name: '',
        password: '',
        role: 'user',
    });

    const isEditing = !!user;

    useEffect(() => {
        if (user) {
            setFormData({
                username: user.username,
                full_name: user.full_name || '',
                password: '', // Пароль завжди пустий при редагуванні
                role: user.role,
            });
        } else {
            // Скидання форми для нового користувача
            setFormData({
                username: '',
                full_name: '',
                password: '',
                role: 'user',
            });
        }
    }, [user, open]);

    const handleChange = (event) => {
        const { name, value } = event.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSave = () => {
        const dataToSend = { ...formData };

        // При редагуванні не відправляємо пароль, якщо він пустий
        if (isEditing && !dataToSend.password) {
            delete dataToSend.password;
        }

        onSave(dataToSend, user?.id);
    };

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
            <DialogTitle>{isEditing ? 'Редагувати користувача' : 'Створити користувача'}</DialogTitle>
            <DialogContent>
                <Box component="form" sx={{ mt: 2 }}>
                    <TextField
                        autoFocus
                        margin="dense"
                        name="username"
                        label="Ім'я користувача"
                        type="text"
                        fullWidth
                        variant="outlined"
                        value={formData.username}
                        onChange={handleChange}
                        required
                        disabled={isEditing} // Не дозволяємо змінювати логін
                    />
                    <TextField
                        margin="dense"
                        name="full_name"
                        label="Повне ім'я"
                        type="text"
                        fullWidth
                        variant="outlined"
                        value={formData.full_name}
                        onChange={handleChange}
                    />
                    <TextField
                        margin="dense"
                        name="password"
                        label={isEditing ? 'Новий пароль (залишіть пустим, щоб не змінювати)' : 'Пароль'}
                        type="password"
                        fullWidth
                        variant="outlined"
                        value={formData.password}
                        onChange={handleChange}
                        required={!isEditing} // Пароль обов'язковий лише при створенні
                    />
                    <FormControl fullWidth margin="dense">
                        <InputLabel>Роль</InputLabel>
                        <Select
                            name="role"
                            value={formData.role}
                            label="Роль"
                            onChange={handleChange}
                        >
                            <MenuItem value="user">User</MenuItem>
                            <MenuItem value="admin">Admin</MenuItem>
                        </Select>
                    </FormControl>
                </Box>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Скасувати</Button>
                <Button onClick={handleSave} variant="contained">Зберегти</Button>
            </DialogActions>
        </Dialog>
    );
};

export default UserFormModal;