// src/pages/APTGroupsPage.jsx
import React, { useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Box, Typography, Button, CircularProgress, Alert, Paper, Snackbar } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';

import aptGroupStore from '../stores/aptGroupStore';
import APTGroupTable from '../components/apt_groups/APTGroupTable'; // Створимо далі
import APTGroupFormModal from '../components/apt_groups/APTGroupFormModal'; // Створимо далі

const APTGroupsPage = observer(() => {
    const [formModalOpen, setFormModalOpen] = useState(false);
    const [editingAptGroup, setEditingAptGroup] = useState(null);
    const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

    useEffect(() => {
        aptGroupStore.fetchAptGroups();
    }, []);

    const handleOpenCreateModal = () => {
        setEditingAptGroup(null);
        setFormModalOpen(true);
    };

    const handleOpenEditModal = (group) => {
        setEditingAptGroup(group);
        setFormModalOpen(true);
    };

    const handleCloseModal = () => {
        setFormModalOpen(false);
        setEditingAptGroup(null);
    };

    const handleSaveAptGroup = async (aptData, groupId) => {
        try {
            let message = '';
            if (groupId) {
                await aptGroupStore.saveAptGroup(groupId, aptData);
                message = 'APT угруповання успішно оновлено!';
            } else {
                await aptGroupStore.addAptGroup(aptData);
                message = 'APT угруповання успішно створено!';
            }
            setSnackbar({ open: true, message, severity: 'success' });
            handleCloseModal();
        } catch (error) {
            setSnackbar({ open: true, message: error.message || 'Не вдалося зберегти APT угруповання.', severity: 'error' });
        }
    };

    const handleDeleteAptGroup = async (groupId) => {
        if (window.confirm(`Ви впевнені, що хочете видалити APT угруповання ID: ${groupId}? Це також відв'яже його від усіх IoC.`)) {
            try {
                await aptGroupStore.removeAptGroup(groupId);
                setSnackbar({ open: true, message: 'APT угруповання успішно видалено!', severity: 'success' });
            } catch (error) {
                setSnackbar({ open: true, message: error.message || 'Не вдалося видалити APT угруповання.', severity: 'error' });
            }
        }
    };

    const handleViewIoCs = (groupId) => {
        // Тут може бути логіка переходу на сторінку деталей APT
        // або відкриття модального вікна зі списком IoC.
        // Наприклад, можна завантажити IoC в aptGroupStore.linkedIoCs
        aptGroupStore.fetchAptGroupById(groupId); // Це завантажить і групу, і пов'язані IoC
        console.log(`View IoCs for APT Group ID: ${groupId}`);
        // Потім можна відобразити aptGroupStore.linkedIoCs в окремому компоненті/модалці
    };

    const handleCloseSnackbar = (event, reason) => {
        if (reason === 'clickaway') return;
        setSnackbar(prev => ({ ...prev, open: false }));
    };

    if (aptGroupStore.isLoading && aptGroupStore.aptGroups.length === 0) {
        return <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px"><CircularProgress /></Box>;
    }

    return (
        <Paper elevation={3} sx={{ p: { xs: 2, sm: 3 } }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} flexWrap="wrap">
                <Typography variant="h4" component="h1" gutterBottom sx={{mr: 2}}>
                    APT Угруповання
                </Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={handleOpenCreateModal}
                >
                    Додати APT
                </Button>
            </Box>

            {aptGroupStore.error && !formModalOpen && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    {String(aptGroupStore.error)}
                </Alert>
            )}
            {/* Можна додати snackbar для aptGroupStore.operationStatus, якщо потрібно */}

            <APTGroupTable
                aptGroups={aptGroupStore.aptGroups}
                onEdit={handleOpenEditModal}
                onDelete={handleDeleteAptGroup}
                onViewIoCs={handleViewIoCs} // Новий обробник
            />

            {formModalOpen && (
                <APTGroupFormModal
                    open={formModalOpen}
                    onClose={handleCloseModal}
                    onSave={handleSaveAptGroup}
                    initialData={editingAptGroup}
                    isLoading={aptGroupStore.isLoading}
                    formError={aptGroupStore.error && formModalOpen ? String(aptGroupStore.error) : null} // Передаємо помилку тільки для форми
                />
            )}
            <Snackbar
                open={snackbar.open}
                autoHideDuration={6000}
                onClose={handleCloseSnackbar}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
            >
                <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }} variant="filled">
                    {snackbar.message}
                </Alert>
            </Snackbar>
        </Paper>
    );
});

export default APTGroupsPage;