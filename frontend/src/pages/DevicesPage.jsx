// src/pages/DevicesPage.jsx
import React, { useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Box, Typography, Button, CircularProgress, Alert, Paper } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';

import deviceStore from '../stores/deviceStore'; // Імпортуємо стор
import DeviceTable from '../components/devices/DeviceTable'; // Компонент таблиці (створимо далі)
import DeviceFormModal from '../components/devices/DeviceFormModal'; // Компонент модального вікна з формою (створимо далі)

const DevicesPage = observer(() => {
    const [isFormModalOpen, setIsFormModalOpen] = useState(false);
    const [editingDevice, setEditingDevice] = useState(null); // Для редагування існуючого пристрою

    useEffect(() => {
        // Завантажуємо пристрої при першому рендері або при зміні пагінації (якщо реалізовано)
        // deviceStore.fetchDevices(deviceStore.pagination.page, deviceStore.pagination.rowsPerPage);
        // Поки що просто завантажимо першу сторінку
        if (deviceStore.devices.length === 0) { // Завантажуємо, тільки якщо список порожній, для уникнення повторних запитів при кожному рендері
            deviceStore.fetchDevices();
        }
    }, []); // Порожній масив залежностей означає, що ефект виконається один раз при монтуванні

    const handleOpenCreateModal = () => {
        setEditingDevice(null); // Скидаємо стан редагування
        setIsFormModalOpen(true);
    };

    const handleOpenEditModal = (device) => {
        setEditingDevice(device);
        setIsFormModalOpen(true);
    };

    const handleCloseModal = () => {
        setIsFormModalOpen(false);
        setEditingDevice(null); // Скидаємо стан редагування при закритті
    };

    const handleSaveDevice = async (deviceDataFromForm, deviceIdToUpdate) => { // deviceIdToUpdate - це initialData.id
        try {
            if (deviceIdToUpdate) { // Якщо є deviceIdToUpdate, це редагування
                await deviceStore.saveDevice(deviceIdToUpdate, deviceDataFromForm);
            } else { // Інакше - створення нового
                await deviceStore.addDevice(deviceDataFromForm);
            }
            handleCloseModal();
            // Оновлення списку після успішного збереження (якщо стор не робить це автоматично)
            // deviceStore.fetchDevices(deviceStore.pagination.page, deviceStore.pagination.rowsPerPage);
        } catch (error) {
            console.error("Failed to save device from page:", error);
            // Тут можна обробити помилку, яку прокинув стор (наприклад, показати сповіщення)
            // deviceStore.error вже має бути встановлено стором, але можна і тут
        }
    };

    const handleDeleteDevice = async (deviceId) => {
        // Тут можна додати модальне вікно для підтвердження видалення
        if (window.confirm(`Ви впевнені, що хочете видалити пристрій ID: ${deviceId}?`)) {
            try {
                await deviceStore.removeDevice(deviceId);
                // deviceStore.fetchDevices(); // Якщо потрібно оновити список
            } catch (error) {
                console.error("Failed to delete device:", error);
            }
        }
    };

    // Додамо обробники для інших дій, наприклад, отримання статусу
    const handleGetStatus = async (deviceId) => {
        try {
            await deviceStore.runGetDeviceStatus(deviceId);
            // Дані оновляться в сторі, таблиця має перерендеритися
        } catch (error) {
            console.error("Failed to get device status:", error);
        }
    };


    if (deviceStore.isLoading && deviceStore.devices.length === 0) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Paper elevation={3} sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h4" component="h1">
                    Управління Пристроями
                </Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={handleOpenCreateModal}
                >
                    Додати Пристрій
                </Button>
            </Box>

            {deviceStore.error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    {typeof deviceStore.error === 'object' ? JSON.stringify(deviceStore.error) : deviceStore.error}
                </Alert>
            )}

            <DeviceTable
                devices={deviceStore.devices}
                onEdit={handleOpenEditModal}
                onDelete={handleDeleteDevice}
                onGetStatus={handleGetStatus}
                // Передамо інші обробники сюди:
                // onConfigureSyslog={(deviceId) => { /* логіка відкриття модалки для syslog */ }}
                // onConfigureNetflow={(deviceId) => { /* логіка відкриття модалки для netflow */ }}
                // onBlockIp={(deviceId) => { /* логіка відкриття модалки для block ip */ }}
            />

            {isFormModalOpen && (
                <DeviceFormModal
                    open={isFormModalOpen}
                    onClose={handleCloseModal}
                    onSave={handleSaveDevice}
                    initialData={editingDevice} // Передаємо дані для редагування або null для створення
                />
            )}
            {/* Тут можна додати інші модальні вікна для конфігурацій та підтверджень */}
        </Paper>
    );
});

export default DevicesPage;