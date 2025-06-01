// src/pages/IoCSourcesPage.jsx
import React, {useEffect, useState} from 'react';
import {observer} from 'mobx-react-lite';
import {Alert, Box, Button, CircularProgress, Paper, Snackbar, Typography} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';

import iocSourceStore from '../stores/iocSourceStore';
import IoCSourceTable from '../components/ioc_sources/IoCSourceTable';
import IoCSourceFormModal from '../components/ioc_sources/IoCSourceFormModal';

const IoCSourcesPage = observer(() => {
    const [formModalOpen, setFormModalOpen] = useState(false);
    const [editingSource, setEditingSource] = useState(null);
    const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

    useEffect(() => {
        iocSourceStore.fetchSources();
    }, []);

    const handleOpenCreateModal = () => {
        iocSourceStore.clearCurrentSource(); // Або setEditingSource(null)
        setEditingSource(null);
        setFormModalOpen(true);
    };

    const handleOpenEditModal = (source) => {
        setEditingSource(source);
        setFormModalOpen(true);
    };

    const handleCloseModal = () => {
        setFormModalOpen(false);
        setEditingSource(null);
    };

    const handleSaveSource = async (sourceData, sourceId) => {
        try {
            let message = '';
            if (sourceId) {
                await iocSourceStore.saveSource(sourceId, sourceData);
                message = 'Джерело IoC успішно оновлено!';
            } else {
                await iocSourceStore.addSource(sourceData);
                message = 'Джерело IoC успішно створено!';
            }
            setSnackbar({ open: true, message, severity: 'success' });
            handleCloseModal();
        } catch (error) {
            console.error("Failed to save IoC source:", error);
            setSnackbar({ open: true, message: error.message || 'Не вдалося зберегти джерело IoC.', severity: 'error' });
        }
    };

    const handleDeleteSource = async (sourceId) => {
        if (window.confirm(`Ви впевнені, що хочете видалити джерело IoC ID: ${sourceId}?`)) {
            try {
                await iocSourceStore.removeSource(sourceId);
                setSnackbar({ open: true, message: 'Джерело IoC успішно видалено!', severity: 'success' });
            } catch (error) {
                console.error("Failed to delete IoC source:", error);
                setSnackbar({ open: true, message: error.message || 'Не вдалося видалити джерело IoC.', severity: 'error' });
            }
        }
    };

    const handleFetchIoCs = async (sourceId) => {
        setSnackbar({ open: true, message: `Запуск завантаження IoC для джерела ID: ${sourceId}...`, severity: 'info' });
        try {
            const result = await iocSourceStore.triggerFetchIoCs(sourceId);
            setSnackbar({ open: true, message: result.message || 'Операція завантаження IoC завершена.', severity: result.status === 'success' ? 'success' : 'warning' });
        } catch (error) {
            setSnackbar({ open: true, message: error.message || 'Помилка під час завантаження IoC.', severity: 'error' });
        }
    };

    const handleCloseSnackbar = (event, reason) => {
        if (reason === 'clickaway') {
            return;
        }
        setSnackbar(prev => ({ ...prev, open: false }));
    };


    if (iocSourceStore.isLoading && iocSourceStore.sources.length === 0) {
        return <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px"><CircularProgress /></Box>;
    }

    return (
        <Paper elevation={3} sx={{ p: { xs: 2, sm: 3 } }}> {/* Адаптивний padding */}
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} flexWrap="wrap">
                <Typography variant="h4" component="h1" gutterBottom sx={{mr: 2}}>
                    Джерела Індикаторів Компрометації (IoC)
                </Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={handleOpenCreateModal}
                >
                    Додати Джерело
                </Button>
            </Box>

            {iocSourceStore.error && !formModalOpen && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    {typeof iocSourceStore.error === 'object' ? JSON.stringify(iocSourceStore.error) : String(iocSourceStore.error)}
                </Alert>
            )}
            {iocSourceStore.fetchStatus && !iocSourceStore.isLoading && (
                <Alert severity={iocSourceStore.error ? "error" : "info"} sx={{ mb: 2 }} onClose={() => iocSourceStore.fetchStatus = ''}>
                    {iocSourceStore.fetchStatus}
                </Alert>
            )}


            <IoCSourceTable
                sources={iocSourceStore.sources}
                onEdit={handleOpenEditModal}
                onDelete={handleDeleteSource}
                onFetchIoCs={handleFetchIoCs}
                // pagination (якщо на сервері)
                // page={iocSourceStore.pagination.page}
                // rowsPerPage={iocSourceStore.pagination.rowsPerPage}
                // count={iocSourceStore.totalSources}
                // onPageChange={(event, newPage) => iocSourceStore.setPagination(newPage, iocSourceStore.pagination.rowsPerPage)}
                // onRowsPerPageChange={(event) => iocSourceStore.setPagination(0, parseInt(event.target.value, 10))}
            />

            {formModalOpen && ( // Показуємо модальне вікно тільки якщо formModalOpen true
                <IoCSourceFormModal
                    open={formModalOpen}
                    onClose={handleCloseModal}
                    onSave={handleSaveSource}
                    initialData={editingSource}
                    isLoading={iocSourceStore.isLoading} // Передаємо стан завантаження для форми
                    // Можна передати специфічну помилку форми, якщо вона є
                    // formError={iocSourceStore.formError}
                />
            )}
            <Snackbar
                open={snackbar.open}
                autoHideDuration={6000}
                onClose={handleCloseSnackbar}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
            >
                <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
                    {snackbar.message}
                </Alert>
            </Snackbar>
        </Paper>
    );
});

export default IoCSourcesPage;