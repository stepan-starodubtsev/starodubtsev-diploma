// src/pages/IndicatorsPage.jsx
import React, { useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Box, Typography, Button, CircularProgress, Alert, Paper, Snackbar, TextField, Select, MenuItem, FormControl, InputLabel, Grid } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import SearchIcon from '@mui/icons-material/Search';

import indicatorStore from '../stores/indicatorStore';
import IndicatorTable from '../components/indicators/IndicatorTable'; // Створимо далі
import IndicatorFormModal from '../components/indicators/IndicatorFormModal.jsx'; // Створимо далі
import LinkAptToIoCModal from '../components/indicators/LinkAptToIoCModal'; // Створимо далі
import { IoCTypeEnum } from '../constants.js';
import aptGroupStore from "../stores/aptGroupStore.js"; // Припускаємо, що Enum тут

const IndicatorsPage = observer(() => {
    const [formModalOpen, setFormModalOpen] = useState(false);
    const [editingIoC, setEditingIoC] = useState(null); // Для редагування
    const [linkingIoC, setLinkingIoC] = useState(null); // Для модалки зв'язування з APT

    const [searchValue, setSearchValue] = useState('');
    const [searchType, setSearchType] = useState(''); // Порожній рядок для "будь-який тип"
    const [filterDate, setFilterDate] = useState('all'); // 'all', 'today'

    useEffect(() => {
        indicatorStore.loadIoCs(); // Початкове завантаження
        aptGroupStore.fetchAptGroups();
        indicatorStore.loadSourceNames();
    }, []);

    const handleSearch = () => {
        indicatorStore.setSearchFilters(searchValue, searchType || null, filterDate);
    };

    const handleResetFilters = () => {
        setSearchValue('');
        setSearchType('');
        setFilterDate('all');
        indicatorStore.setSearchFilters('', null, 'all');
    };


    const handleOpenCreateModal = () => {
        setEditingIoC(null);
        setFormModalOpen(true);
    };

    const handleOpenEditModal = (ioc) => {
        setEditingIoC(ioc);
        setFormModalOpen(true);
    };

    const handleOpenLinkAptModal = (ioc) => {
        setLinkingIoC(ioc); // Передаємо весь об'єкт IoC або тільки ioc_id
    };

    const handleCloseModal = () => {
        setFormModalOpen(false);
        setEditingIoC(null);
        setLinkingIoC(null);
    };

    const handleSaveIoC = async (iocData, iocEsId) => {
        try {
            let message = '';
            if (iocEsId) {
                await indicatorStore.saveIoC(iocEsId, iocData);
                message = 'Індикатор успішно оновлено!';
            } else {
                await indicatorStore.createIoC(iocData);
                message = 'Індикатор успішно створено!';
            }
            setSnackbar({ open: true, message, severity: 'success' });
            handleCloseModal();
        } catch (error) {
            setSnackbar({ open: true, message: error.message || 'Не вдалося зберегти індикатор.', severity: 'error' });
        }
    };

    const handleDeleteIoC = async (iocEsId) => {
        if (window.confirm(`Ви впевнені, що хочете видалити індикатор ID: ${iocEsId}?`)) {
            try {
                await indicatorStore.removeIoC(iocEsId);
                setSnackbar({ open: true, message: 'Індикатор успішно видалено!', severity: 'success' });
            } catch (error) {
                setSnackbar({ open: true, message: error.message || 'Не вдалося видалити індикатор.', severity: 'error' });
            }
        }
    };

    const handleLinkApt = async (iocEsId, aptGroupId) => {
        try {
            await indicatorStore.performLinkIoCToApt(iocEsId, aptGroupId);
            setSnackbar({ open: true, message: `IoC ${iocEsId} прив'язано до APT ID ${aptGroupId}`, severity: 'success'});
            indicatorStore.loadIoCs(); // Оновити список, щоб побачити зміни в тегах/ID APT
            handleCloseModal(); // Закрити модалку зв'язування
        } catch (error) {
            setSnackbar({ open: true, message: error.message || 'Помилка прив\'язки APT до IoC', severity: 'error'});
        }
    };

    const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
    const handleCloseSnackbar = (event, reason) => {
        if (reason === 'clickaway') return;
        setSnackbar(prev => ({ ...prev, open: false }));
    };


    if (indicatorStore.isLoading && indicatorStore.iocs.length === 0 && !indicatorStore.error) {
        return <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px"><CircularProgress /></Box>;
    }

    return (
        <Paper elevation={3} sx={{ p: { xs: 2, sm: 3 } }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} flexWrap="wrap">
                <Typography variant="h4" component="h1" gutterBottom sx={{mr: 2}}>
                    Індикатори Компрометації (IoC)
                </Typography>
                <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={handleOpenCreateModal}>
                    Додати IoC
                </Button>
            </Box>

            {/* Фільтри та Пошук */}
            <Box component={Paper} elevation={1} sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>Фільтри та Пошук</Typography>
                <Grid container spacing={2} alignItems="flex-end">
                    <Grid item size={2}>
                        <TextField
                            fullWidth label="Значення IoC" variant="outlined" size="small"
                            value={searchValue} onChange={(e) => setSearchValue(e.target.value)}
                        />
                    </Grid>
                    <Grid item size={2}>
                        <FormControl fullWidth size="small" variant="outlined">
                            <InputLabel>Тип IoC</InputLabel>
                            <Select
                                value={searchType}
                                onChange={(e) => setSearchType(e.target.value)}
                                label="Тип IoC"
                            >
                                <MenuItem value=""><em>Будь-який</em></MenuItem>
                                {Object.entries(IoCTypeEnum).map(([key, val]) => (
                                    <MenuItem key={val} value={val}>{key.replace("_", " ")}</MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid item size={2}>
                        <FormControl fullWidth size="small" variant="outlined">
                            <InputLabel>Дата Створення</InputLabel>
                            <Select
                                value={filterDate}
                                onChange={(e) => setFilterDate(e.target.value)}
                                label="Дата Створення"
                            >
                                <MenuItem value="all">Всі</MenuItem>
                                <MenuItem value="today">За сьогодні</MenuItem>
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid item xs={12} sm={1}>
                        <Button variant="contained" onClick={handleSearch} startIcon={<SearchIcon />} fullWidth>
                            Пошук
                        </Button>
                    </Grid>
                    <Grid item xs={12} sm={1}>
                        <Button variant="outlined" onClick={handleResetFilters} fullWidth>
                            Скинути
                        </Button>
                    </Grid>
                </Grid>
            </Box>

            {indicatorStore.error && !formModalOpen && (
                <Alert severity="error" sx={{ mb: 2 }}>{String(indicatorStore.error)}</Alert>
            )}
            {indicatorStore.operationStatus && !indicatorStore.isLoading && (
                <Alert severity={indicatorStore.error ? "error" : "success"} sx={{ mb: 2 }} onClose={() => indicatorStore.operationStatus = ''}>
                    {indicatorStore.operationStatus}
                </Alert>
            )}

            <IndicatorTable
                iocs={indicatorStore.displayableIoCs} // Використовуємо displayableIoCs
                onEdit={handleOpenEditModal}
                onDelete={handleDeleteIoC}
                onLinkApt={handleOpenLinkAptModal}
                // Пагінація
                page={indicatorStore.pagination.page}
                rowsPerPage={indicatorStore.pagination.rowsPerPage}
                count={indicatorStore.totalIoCs} // Загальна кількість для серверної пагінації
                onPageChange={(event, newPage) => indicatorStore.setPagination(newPage, indicatorStore.pagination.rowsPerPage)}
                onRowsPerPageChange={(event) => indicatorStore.setPagination(0, parseInt(event.target.value, 10))}
            />

            {formModalOpen && (
                <IndicatorFormModal
                    open={formModalOpen}
                    onClose={handleCloseModal}
                    onSave={handleSaveIoC}
                    initialData={editingIoC}
                    isLoading={indicatorStore.isLoading}
                    formError={indicatorStore.error && formModalOpen ? String(indicatorStore.error) : null}
                    sourceNames={indicatorStore.sourceNames} // NEW: Передаємо список джерел
                />
            )}
            {linkingIoC && (
                <LinkAptToIoCModal
                    open={!!linkingIoC}
                    onClose={handleCloseModal}
                    onLink={handleLinkApt}
                    ioc={linkingIoC} // Передаємо об'єкт IoC
                    aptGroupStore={aptGroupStore} // Приклад
                />
            )}

            <Snackbar
                open={snackbar.open}
                autoHideDuration={4000}
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

export default IndicatorsPage;