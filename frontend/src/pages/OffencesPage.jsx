// src/pages/OffencesPage.jsx
import React, { useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Box, Typography, CircularProgress, Alert, Paper, Snackbar, Grid, TextField, Button, FormControl, InputLabel, Select, MenuItem } from '@mui/material';

import offenceStore from '../stores/offenceStore';
import OffenceTable from '../components/offences/OffenceTable'; // Створимо далі
import OffenceDetailsModal from '../components/offences/OffenceDetailsModal'; // Створимо далі
import { OffenceStatusEnum, OffenceSeverityEnum, OffenceStatusLabels, OffenceSeverityLabels } from '../constants'; // Припускаємо, що Enum та мітки тут

const OffencesPage = observer(() => {
    const [detailsModalOpen, setDetailsModalOpen] = useState(false);
    const [selectedOffence, setSelectedOffence] = useState(null);
    const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

    // Фільтри
    const [filterStatus, setFilterStatus] = useState('');
    const [filterSeverity, setFilterSeverity] = useState('');

    useEffect(() => {
        // Завантажуємо офенси при першому рендері або зміні фільтрів/пагінації
        offenceStore.fetchOffences();
    }, [offenceStore.pagination.page, offenceStore.pagination.rowsPerPage]); // Додай залежність від фільтрів, якщо вони впливають на fetchOffences

    const handleApplyFilters = () => {
        offenceStore.setFilters(filterStatus || null, filterSeverity || null);
    };

    const handleResetFilters = () => {
        setFilterStatus('');
        setFilterSeverity('');
        offenceStore.setFilters(null, null);
    };

    const handleViewDetails = (offence) => {
        offenceStore.fetchOffenceById(offence.id); // Завантажуємо деталі
        setSelectedOffence(offence); // Можна одразу передати, якщо в таблиці є всі дані
        setDetailsModalOpen(true);
    };

    const handleCloseDetailsModal = () => {
        setDetailsModalOpen(false);
        setSelectedOffence(null);
        offenceStore.clearCurrentOffence();
    };

    const handleUpdateOffence = async (offenceId, status, notes, severity) => {
        try {
            await offenceStore.updateStatus(offenceId, status, notes, severity);
            setSnackbar({ open: true, message: `Офенс ID ${offenceId} оновлено.`, severity: 'success' });
            handleCloseDetailsModal(); // Закриваємо модалку після оновлення
        } catch (error) {
            setSnackbar({ open: true, message: error.message || 'Не вдалося оновити офенс.', severity: 'error' });
        }
    };

    const handleCloseSnackbar = (event, reason) => {
        if (reason === 'clickaway') return;
        setSnackbar(prev => ({ ...prev, open: false }));
    };


    if (offenceStore.isLoading && offenceStore.offences.length === 0 && !offenceStore.error) {
        return <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px"><CircularProgress /></Box>;
    }

    return (
        <Paper elevation={3} sx={{ p: { xs: 2, sm: 3 } }}>
            <Typography variant="h4" component="h1" gutterBottom>
                Офенси (Інциденти)
            </Typography>

            {/* Фільтри */}
            <Box component={Paper} elevation={1} sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>Фільтри</Typography>
                <Grid container spacing={2} alignItems="flex-end">
                    <Grid item size={3}>
                        <FormControl fullWidth size="small" variant="outlined">
                            <InputLabel>Статус</InputLabel>
                            <Select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} label="Статус">
                                <MenuItem value=""><em>Всі Статуси</em></MenuItem>
                                {OffenceStatusLabels.map(s => <MenuItem key={s.value} value={s.value}>{s.label}</MenuItem>)}
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid item size={3}>
                        <FormControl fullWidth size="small" variant="outlined">
                            <InputLabel>Серйозність</InputLabel>
                            <Select value={filterSeverity} onChange={(e) => setFilterSeverity(e.target.value)} label="Серйозність">
                                <MenuItem value=""><em>Всі Рівні</em></MenuItem>
                                {OffenceSeverityLabels.map(s => <MenuItem key={s.value} value={s.value}>{s.label}</MenuItem>)}
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid item size={1}>
                        <Button variant="contained" onClick={handleApplyFilters} fullWidth>Застосувати</Button>
                    </Grid>
                    <Grid item size={1}>
                        <Button variant="outlined" onClick={handleResetFilters} fullWidth>Скинути</Button>
                    </Grid>
                </Grid>
            </Box>

            {offenceStore.error && (
                <Alert severity="error" sx={{ mb: 2 }}>{String(offenceStore.error)}</Alert>
            )}
            {offenceStore.operationStatus && !offenceStore.isLoading && (
                <Alert
                    severity={offenceStore.error && offenceStore.operationStatus.startsWith("Помилка") ? "error" : "success"}
                    sx={{ mb: 2 }}
                    onClose={() => offenceStore.operationStatus = ''}
                >
                    {offenceStore.operationStatus}
                </Alert>
            )}

            <OffenceTable
                offences={offenceStore.offences}
                onViewDetails={handleViewDetails}
                // Пагінація
                page={offenceStore.pagination.page}
                rowsPerPage={offenceStore.pagination.rowsPerPage}
                count={offenceStore.totalOffences} // Або offenceStore.offences.length для клієнтської
                onPageChange={(event, newPage) => offenceStore.setPagination(newPage, offenceStore.pagination.rowsPerPage)}
                onRowsPerPageChange={(event) => offenceStore.setPagination(0, parseInt(event.target.value, 10))}
            />

            {selectedOffence && detailsModalOpen && (
                <OffenceDetailsModal
                    open={detailsModalOpen}
                    onClose={handleCloseDetailsModal}
                    offence={offenceStore.currentOffence || selectedOffence} // Передаємо поточний завантажений офенс
                    onUpdate={handleUpdateOffence}
                    isLoading={offenceStore.isLoadingOffences || offenceStore.isLoading} // Можна об'єднати
                />
            )}
            <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={handleCloseSnackbar} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
                <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }} variant="filled">
                    {snackbar.message}
                </Alert>
            </Snackbar>
        </Paper>
    );
});

export default OffencesPage;