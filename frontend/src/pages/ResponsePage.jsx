// src/pages/ResponsePage.jsx
import React, { useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Box, Typography, Button, CircularProgress, Alert, Paper, Snackbar, Tabs, Tab } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import PlayArrowIcon from '@mui/icons-material/PlayArrow'; // Для запуску пайплайну (якщо потрібно)

import responseStore from '../stores/responseStore';
// import offenceStore from '../stores/offenceStore'; // Якщо потрібен список офенсів для вибору
import ResponseActionTable from '../components/response/ResponseActionTable'; // Створимо
import ResponseActionFormModal from '../components/response/ResponseActionFormModal'; // Створимо
import ResponsePipelineTable from '../components/response/ResponsePipelineTable'; // Створимо
import ResponsePipelineFormModal from '../components/response/ResponsePipelineFormModal'; // Створимо
// import TriggerResponseModal from '../components/response/TriggerResponseModal'; // Для ручного запуску

const TabPanel = (props) => {
    const { children, value, index, ...other } = props;
    return (
        <div role="tabpanel" hidden={value !== index} id={`response-tabpanel-${index}`} aria-labelledby={`response-tab-${index}`} {...other}>
            {value === index && (<Box sx={{ pt: 3 }}>{children}</Box>)}
        </div>
    );
};

const ResponsePage = observer(() => {
    const [currentTab, setCurrentTab] = useState(0); // 0 для Actions, 1 для Pipelines

    const [actionFormModalOpen, setActionFormModalOpen] = useState(false);
    const [editingAction, setEditingAction] = useState(null);

    const [pipelineFormModalOpen, setPipelineFormModalOpen] = useState(false);
    const [editingPipeline, setEditingPipeline] = useState(null);

    // const [triggerModalOpen, setTriggerModalOpen] = useState(false);
    // const [selectedOffenceIdForTrigger, setSelectedOffenceIdForTrigger] = useState(null);


    const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

    useEffect(() => {
        if (currentTab === 0) responseStore.fetchActions();
        else if (currentTab === 1) responseStore.fetchPipelines();
    }, [currentTab]);

    const handleTabChange = (event, newValue) => setCurrentTab(newValue);
    const handleCloseSnackbar = (event, reason) => { if (reason === 'clickaway') return; setSnackbar(prev => ({ ...prev, open: false })); };

    // --- Обробники для Actions ---
    const handleOpenCreateActionModal = () => { setEditingAction(null); setActionFormModalOpen(true); };
    const handleOpenEditActionModal = (action) => { setEditingAction(action); setActionFormModalOpen(true); };
    const handleCloseActionModal = () => { setActionFormModalOpen(false); setEditingAction(null); };
    const handleSaveAction = async (data, id) => {
        try {
            const message = id ? await responseStore.saveAction(id, data) : await responseStore.addAction(data);
            setSnackbar({ open: true, message: id ? 'Дію оновлено!' : 'Дію створено!', severity: 'success' });
            handleCloseActionModal();
        } catch (e) { setSnackbar({ open: true, message: e.message || 'Помилка збереження дії.', severity: 'error' });}
    };
    const handleDeleteAction = async (id) => { /* ... реалізація ... */ };

    // --- Обробники для Pipelines ---
    const handleOpenCreatePipelineModal = () => { setEditingPipeline(null); setPipelineFormModalOpen(true); };
    const handleOpenEditPipelineModal = (pipeline) => { setEditingPipeline(pipeline); setPipelineFormModalOpen(true); };
    const handleClosePipelineModal = () => { setPipelineFormModalOpen(false); setEditingPipeline(null); };
    const handleSavePipeline = async (data, id) => {
        try {
            const message = id ? await responseStore.savePipeline(id, data) : await responseStore.addPipeline(data);
            setSnackbar({ open: true, message: id ? 'Пайплайн оновлено!' : 'Пайплайн створено!', severity: 'success' });
            handleClosePipelineModal();
        } catch (e) { setSnackbar({ open: true, message: e.message || 'Помилка збереження пайплайну.', severity: 'error' });}
    };
    const handleDeletePipeline = async (id) => { /* ... реалізація ... */ };

    // const handleTriggerResponse = async (offenceId) => { /* ... */ };


    return (
        <Paper elevation={3} sx={{ p: { xs: 2, sm: 3 } }}>
            <Typography variant="h4" component="h1" gutterBottom>
                Управління Реагуванням
            </Typography>
            {/* <Button
        variant="outlined"
        onClick={() => setTriggerModalOpen(true)}
        startIcon={<PlayArrowIcon/>}
        sx={{mb:2}}
      >
        Запустити Реагування для Офенса
      </Button>
      */}

            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={currentTab} onChange={handleTabChange} aria-label="Response management tabs">
                    <Tab label="Дії Реагування" id="response-tab-0" aria-controls="response-tabpanel-0" />
                    <Tab label="Пайплайни Реагування" id="response-tab-1" aria-controls="response-tabpanel-1" />
                </Tabs>
            </Box>

            <TabPanel value={currentTab} index={0}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} mt={1}>
                    <Typography variant="h5">Список Дій</Typography>
                    <Button variant="contained" startIcon={<AddIcon />} onClick={handleOpenCreateActionModal}>
                        Створити Дію
                    </Button>
                </Box>
                {responseStore.isLoadingActions && responseStore.actions.length === 0 && <CircularProgress />}
                {responseStore.error && currentTab === 0 && <Alert severity="error" sx={{ mb: 2 }}>{String(responseStore.error)}</Alert>}
                <ResponseActionTable
                    actions={responseStore.actions}
                    onEdit={handleOpenEditActionModal}
                    onDelete={handleDeleteAction}
                />
            </TabPanel>

            <TabPanel value={currentTab} index={1}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} mt={1}>
                    <Typography variant="h5">Список Пайплайнів</Typography>
                    <Button variant="contained" startIcon={<AddIcon />} onClick={handleOpenCreatePipelineModal}>
                        Створити Пайплайн
                    </Button>
                </Box>
                {responseStore.isLoadingPipelines && responseStore.pipelines.length === 0 && <CircularProgress />}
                {responseStore.error && currentTab === 1 && <Alert severity="error" sx={{ mb: 2 }}>{String(responseStore.error)}</Alert>}
                <ResponsePipelineTable
                    pipelines={responseStore.pipelines}
                    onEdit={handleOpenEditPipelineModal}
                    onDelete={handleDeletePipeline}
                />
            </TabPanel>

            {actionFormModalOpen && (
                <ResponseActionFormModal
                    open={actionFormModalOpen}
                    onClose={handleCloseActionModal}
                    onSave={handleSaveAction}
                    initialData={editingAction}
                    isLoading={responseStore.isLoadingActions}
                    formError={responseStore.error && actionFormModalOpen ? String(responseStore.error) : null}
                />
            )}

            {pipelineFormModalOpen && (
                <ResponsePipelineFormModal
                    open={pipelineFormModalOpen}
                    onClose={handleClosePipelineModal}
                    onSave={handleSavePipeline}
                    initialData={editingPipeline}
                    isLoading={responseStore.isLoadingPipelines}
                    formError={responseStore.error && pipelineFormModalOpen ? String(responseStore.error) : null}
                    // Потрібно передати список доступних дій для вибору в формі пайплайна
                    availableActions={responseStore.actions}
                />
            )}
            {/* {triggerModalOpen && (
        <TriggerResponseModal
            open={triggerModalOpen}
            onClose={() => setTriggerModalOpen(false)}
            onTrigger={handleTriggerResponse}
            // offenceStore={offenceStore} // Для вибору офенса
            isLoading={responseStore.isLoadingPipelines} // Можна використовувати isLoadingPipelines
        />
      )}
      */}

            <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={handleCloseSnackbar} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
                <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }} variant="filled">
                    {snackbar.message}
                </Alert>
            </Snackbar>
        </Paper>
    );
});

export default ResponsePage;