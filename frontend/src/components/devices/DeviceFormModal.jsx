// src/components/devices/DeviceFormModal.jsx
import React, {useEffect, useState} from 'react';
import {
    Alert,
    Button,
    Checkbox,
    CircularProgress,
    Dialog,
    DialogActions,
    DialogContent,
    DialogContentText,
    DialogTitle,
    FormControl,
    FormControlLabel,
    InputLabel,
    MenuItem,
    Select,
    TextField
} from '@mui/material';

// Припускаємо, що DeviceTypeEnum визначено десь глобально або імпортовано
// з твоїх схем (якщо вони доступні на фронтенді, це краще)
// import { DeviceTypeEnum } from '../../schemas'; // Або відповідний шлях
// Або просто хардкодимо значення для форми, як раніше:
const deviceTypes = [
    { value: 'mikrotik_routeros', label: 'Mikrotik RouterOS' },
    // Додай інші типи, якщо потрібно
];

const initialFormState = {
    name: '',
    host: '',
    port: 8728, // Стандартний порт для Mikrotik API (не SSL)
    username: '',
    password: '',
    device_type: 'mikrotik_routeros', // Значення за замовчуванням
    is_enabled: true,
};

const DeviceFormModal = ({ open, onClose, onSave, initialData, isLoading, error }) => {
    const [formData, setFormData] = useState(initialFormState);
    const [formErrors, setFormErrors] = useState({}); // Для помилок валідації

    useEffect(() => {
        if (initialData) {
            setFormData({
                name: initialData.name || '',
                host: initialData.host || '',
                port: initialData.port || 8728,
                username: initialData.username || '',
                password: '', // Пароль завжди порожній для безпеки при редагуванні
                device_type: initialData.device_type?.value || initialData.device_type || 'mikrotik_routeros',
                is_enabled: initialData.is_enabled !== undefined ? initialData.is_enabled : true,
            });
        } else {
            setFormData(initialFormState); // Скидаємо до початкового стану для нового пристрою
        }
        setFormErrors({}); // Скидаємо помилки при відкритті/зміні даних
    }, [initialData, open]); // Залежність від open, щоб скидати форму при кожному відкритті

    const handleChange = (event) => {
        const { name, value, type, checked } = event.target;
        setFormData(prevFormData => ({
            ...prevFormData,
            [name]: type === 'checkbox' ? checked : value,
        }));
        // Скидаємо помилку для поля, яке змінюється
        if (formErrors[name]) {
            setFormErrors(prevErrors => ({...prevErrors, [name]: ''}));
        }
    };

    const validateForm = () => {
        const errors = {};
        if (!formData.name.trim()) errors.name = "Назва пристрою є обов'язковою";
        else if (formData.name.trim().length < 3) errors.name = "Назва має містити щонайменше 3 символи";

        if (!formData.host.trim()) errors.host = "Хост є обов'язковим";
        // Тут можна додати валідацію IP/DNS за допомогою регулярного виразу

        if (!formData.port) errors.port = "Порт є обов'язковим";
        else if (isNaN(formData.port) || Number(formData.port) <= 0 || Number(formData.port) > 65535) {
            errors.port = "Некоректний номер порту";
        }

        if (!formData.username.trim()) errors.username = "Ім'я користувача є обов'язковим";

        // Пароль обов'язковий тільки при створенні нового пристрою (коли немає initialData)
        if (!initialData && !formData.password) {
            errors.password = "Пароль є обов'язковим для нового пристрою";
        } else if (formData.password && formData.password.length < 1) { // Якщо пароль введено, але короткий
            // Можна додати перевірку на мінімальну довжину, якщо потрібно
            // errors.password = "Пароль занадто короткий";
        }


        if (!formData.device_type) errors.device_type = "Тип пристрою є обов'язковим";

        setFormErrors(errors);
        return Object.keys(errors).length === 0; // Повертає true, якщо помилок немає
    };

    const handleSubmit = async (event) => {
        event.preventDefault(); // Запобігаємо стандартній відправці форми
        if (validateForm()) {
            const dataToSave = { ...formData };
            // Якщо це редагування і поле пароля порожнє, не надсилаємо його
            if (initialData && !formData.password) {
                delete dataToSave.password;
            }
            // Видаляємо id, якщо це створення нового (хоча ми його не додавали в formData)
            if (!initialData) {
                delete dataToSave.id; // На випадок, якщо він якось потрапив
            }

            await onSave(dataToSave, initialData?.id); // Передаємо ID для оновлення
        }
    };

    return (
        <Dialog open={open} onClose={onClose} PaperProps={{ component: 'form', onSubmit: handleSubmit }}>
            <DialogTitle>{initialData ? 'Редагувати Пристрій' : 'Додати Новий Пристрій'}</DialogTitle>
            <DialogContent>
                <DialogContentText sx={{mb: 2}}>
                    {initialData ? 'Внесіть зміни та збережіть.' : 'Заповніть інформацію про новий пристрій.'}
                </DialogContentText>

                {/* Поле для відображення загальних помилок від сервера */}
                {error && <Alert severity="error" sx={{ mb: 2 }}>{typeof error === 'object' ? JSON.stringify(error) : error}</Alert>}

                <TextField
                    autoFocus
                    margin="dense"
                    id="name"
                    name="name"
                    label="Назва пристрою"
                    type="text"
                    fullWidth
                    variant="outlined"
                    value={formData.name}
                    onChange={handleChange}
                    error={!!formErrors.name}
                    helperText={formErrors.name}
                    disabled={isLoading}
                />
                <TextField
                    margin="dense"
                    id="host"
                    name="host"
                    label="Хост (IP або DNS)"
                    type="text"
                    fullWidth
                    variant="outlined"
                    value={formData.host}
                    onChange={handleChange}
                    error={!!formErrors.host}
                    helperText={formErrors.host}
                    disabled={isLoading}
                />
                <TextField
                    margin="dense"
                    id="port"
                    name="port"
                    label="Порт API"
                    type="number"
                    fullWidth
                    variant="outlined"
                    value={formData.port}
                    onChange={handleChange}
                    error={!!formErrors.port}
                    helperText={formErrors.port}
                    disabled={isLoading}
                />
                <TextField
                    margin="dense"
                    id="username"
                    name="username"
                    label="Ім'я користувача (API)"
                    type="text"
                    fullWidth
                    variant="outlined"
                    value={formData.username}
                    onChange={handleChange}
                    error={!!formErrors.username}
                    helperText={formErrors.username}
                    disabled={isLoading}
                />
                <TextField
                    margin="dense"
                    id="password"
                    name="password"
                    label={initialData ? "Новий пароль (залиште порожнім, щоб не змінювати)" : "Пароль (API)"}
                    type="password"
                    fullWidth
                    variant="outlined"
                    value={formData.password}
                    onChange={handleChange}
                    error={!!formErrors.password}
                    helperText={formErrors.password}
                    disabled={isLoading}
                    autoComplete="new-password" // Для уникнення автозаповнення
                />
                <FormControl fullWidth margin="dense" variant="outlined" error={!!formErrors.device_type}>
                    <InputLabel id="device-type-select-label">Тип пристрою</InputLabel>
                    <Select
                        labelId="device-type-select-label"
                        id="device_type"
                        name="device_type"
                        value={formData.device_type}
                        onChange={handleChange}
                        label="Тип пристрою"
                        disabled={isLoading}
                    >
                        {deviceTypes.map((option) => (
                            <MenuItem key={option.value} value={option.value}>
                                {option.label}
                            </MenuItem>
                        ))}
                    </Select>
                    {formErrors.device_type && (
                        <Typography color="error" variant="caption" sx={{ml: 2}}>{formErrors.device_type}</Typography>
                    )}
                </FormControl>
                <FormControlLabel
                    control={
                        <Checkbox
                            checked={formData.is_enabled}
                            onChange={handleChange}
                            name="is_enabled"
                            color="primary"
                            disabled={isLoading}
                        />
                    }
                    label="Пристрій активний"
                    sx={{mt: 1}}
                />
            </DialogContent>
            <DialogActions sx={{p: '0 24px 20px 24px'}}>
                <Button onClick={onClose} disabled={isLoading}>Скасувати</Button>
                <Button type="submit" variant="contained" disabled={isLoading}>
                    {isLoading ? <CircularProgress size={24} /> : (initialData ? 'Зберегти Зміни' : 'Створити Пристрій')}
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default DeviceFormModal;