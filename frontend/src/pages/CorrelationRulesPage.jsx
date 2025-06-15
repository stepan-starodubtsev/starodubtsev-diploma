// src/pages/CorrelationRulesPage.jsx
import React, { useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Box, Typography, Button, CircularProgress, Alert, Paper, Snackbar, Divider } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';

import correlationStore from '../stores/correlationStore';
import CorrelationRuleTable from '../components/correlation/CorrelationRuleTable'; // Створимо
import CorrelationRuleFormModal from '../components/correlation/CorrelationRuleFormModal';
import indicatorStore from "../stores/indicatorStore.js"; // Створимо

const CorrelationRulesPage = observer(() => {
    const [formModalOpen, setFormModalOpen] = useState(false);
    const [editingRule, setEditingRule] = useState(null);
    const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

    useEffect(() => {
        correlationStore.fetchRules();
        indicatorStore.loadUniqueTags();
    }, []);

    const handleOpenCreateModal = () => { setEditingRule(null); setFormModalOpen(true); };
    const handleOpenEditModal = (rule) => { setEditingRule(rule); setFormModalOpen(true); };
    const handleCloseModal = () => { setFormModalOpen(false); setEditingRule(null); };

    const handleSaveRule = async (ruleData, ruleId) => {
        try {
            let message = '';
            if (ruleId) {
                await correlationStore.saveRule(ruleId, ruleData);
                message = 'Правило кореляції успішно оновлено!';
            } else {
                await correlationStore.addRule(ruleData);
                message = 'Правило кореляції успішно створено!';
            }
            setSnackbar({ open: true, message, severity: 'success' });
            handleCloseModal();
        } catch (error) {
            setSnackbar({ open: true, message: error.message || 'Не вдалося зберегти правило.', severity: 'error' });
        }
    };

    const handleDeleteRule = async (ruleId) => {
        if (window.confirm(`Ви впевнені, що хочете видалити правило ID: ${ruleId}?`)) {
            try {
                await correlationStore.removeRule(ruleId);
                setSnackbar({ open: true, message: 'Правило успішно видалено!', severity: 'success' });
            } catch (error) {
                setSnackbar({ open: true, message: error.message || 'Не вдалося видалити правило.', severity: 'error' });
            }
        }
    };

    const handleRunCycle = async () => {
        try {
            const result = await correlationStore.runCorrelationCycle();
            setSnackbar({ open: true, message: result.message || 'Цикл кореляції запущено.', severity: 'info' });
        } catch (error) {
            setSnackbar({ open: true, message: error.message || 'Помилка запуску циклу кореляції.', severity: 'error' });
        }
    };

    const handleLoadDefaults = async () => {
        try {
            const result = await correlationStore.runLoadDefaultRules();
            setSnackbar({ open: true, message: result.message || 'Завантаження дефолтних правил завершено.', severity: 'info' });
        } catch (error) {
            setSnackbar({ open: true, message: error.message || 'Помилка завантаження дефолтних правил.', severity: 'error' });
        }
    };

    const handleCloseSnackbar = (event, reason) => {
        if (reason === 'clickaway') return;
        setSnackbar(prev => ({ ...prev, open: false }));
    };

    return (
        <Paper elevation={3} sx={{ p: { xs: 2, sm: 3 } }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} flexWrap="wrap">
                <Typography variant="h4" component="h1" gutterBottom sx={{ mr: 2 }}>
                    Правила Кореляції
                </Typography>
                <Box>
                    <Button variant="outlined" color="secondary" startIcon={<CloudDownloadIcon />} onClick={handleLoadDefaults} sx={{ mr: 1, mb: { xs: 1, sm: 0 } }}>
                        Завантажити Дефолтні
                    </Button>
                    <Button variant="outlined" color="info" startIcon={<PlayArrowIcon />} onClick={handleRunCycle} sx={{ mr: 1, mb: { xs: 1, sm: 0 } }}>
                        Запустити Кореляцію
                    </Button>
                    <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={handleOpenCreateModal}>
                        Додати Правило
                    </Button>
                </Box>
            </Box>
            <Divider sx={{ my: 2 }} />

            {correlationStore.isLoading && correlationStore.rules.length === 0 && <CircularProgress />}
            {correlationStore.error && !formModalOpen && (
                <Alert severity="error" sx={{ mb: 2 }}>{String(correlationStore.error)}</Alert>
            )}
            {correlationStore.operationStatus && !correlationStore.isLoading && (
                <Alert
                    severity={correlationStore.error && correlationStore.operationStatus.startsWith("Помилка") ? "error" : "info"}
                    sx={{ mb: 2 }}
                    onClose={() => correlationStore.operationStatus = ''}
                >
                    {correlationStore.operationStatus}
                </Alert>
            )}

            <CorrelationRuleTable
                rules={correlationStore.rules}
                onEdit={handleOpenEditModal}
                onDelete={handleDeleteRule}
                // ... (props для пагінації, якщо потрібно)
            />

            {formModalOpen && (
                <CorrelationRuleFormModal
                    open={formModalOpen}
                    onClose={handleCloseModal}
                    onSave={handleSaveRule}
                    initialData={editingRule}
                    isLoading={correlationStore.isLoading}
                    formError={correlationStore.error && formModalOpen ? String(correlationStore.error) : null}
                    allPossibleTags={indicatorStore.uniqueTags}
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

export default CorrelationRulesPage;