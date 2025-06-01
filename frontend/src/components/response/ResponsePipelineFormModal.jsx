// src/components/response/ResponsePipelineFormModal.jsx
import React, { useState, useEffect } from 'react';
import {
    Dialog, DialogActions, DialogContent, DialogTitle, TextField, Button,
    Checkbox, FormControlLabel, CircularProgress, Alert, Box, Typography, Grid
} from '@mui/material';
// import correlationStore from '../../stores/correlationStore'; // Для вибору correlation_rule_id
// import responseStore from '../../stores/responseStore'; // Для вибору action_id

const initialFormState = {
    name: '',
    description: '',
    is_enabled: true,
    trigger_correlation_rule_id: null, // або ''
    actions_config_json: '[]', // Будемо редагувати як JSON рядок для MVP
};

const ResponsePipelineFormModal = ({
                                       open, onClose, onSave, initialData, isLoading, formError,
                                       availableActions, // Список доступних ResponseAction [{id, name}, ...]
                                       availableRules // Список доступних CorrelationRule [{id, name}, ...]
                                   }) => {
    const [formData, setFormData] = useState(initialFormState);
    const [errors, setErrors] = useState({});

    useEffect(() => {
        if (open) {
            if (initialData) {
                setFormData({
                    name: initialData.name || '',
                    description: initialData.description || '',
                    is_enabled: initialData.is_enabled !== undefined ? initialData.is_enabled : true,
                    trigger_correlation_rule_id: initialData.trigger_correlation_rule_id || '',
                    actions_config_json: initialData.actions_config ? JSON.stringify(initialData.actions_config, null, 2) : '[]',
                });
            } else {
                setFormData(initialFormState);
            }
            setErrors({});
        }
    }, [initialData, open]);

    const handleChange = (event) => {
        const { name, value, type, checked } = event.target;
        setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
        if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }));
    };

    const validate = () => {
        const tempErrors = {};
        if (!formData.name.trim()) tempErrors.name = "Назва пайплайна є обов'язковою";
        if (formData.trigger_correlation_rule_id && isNaN(parseInt(formData.trigger_correlation_rule_id))) {
            tempErrors.trigger_correlation_rule_id = "ID правила має бути числом";
        }
        try {
            const parsedActions = JSON.parse(formData.actions_config_json);
            if (!Array.isArray(parsedActions)) throw new Error("Має бути масивом");
            for (const action of parsedActions) {
                if (typeof action.action_id !== 'number' || typeof action.order !== 'number') {
                    throw new Error("Кожна дія має містити 'action_id' (число) та 'order' (число)");
                }
            }
        } catch (e) {
            tempErrors.actions_config_json = `Некоректний JSON для конфігурації дій: ${e.message}`;
        }
        setErrors(tempErrors);
        return Object.keys(tempErrors).length === 0;
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        if (validate()) {
            try {
                const actions_config = JSON.parse(formData.actions_config_json);
                const dataToSave = {
                    name: formData.name,
                    description: formData.description,
                    is_enabled: formData.is_enabled,
                    trigger_correlation_rule_id: formData.trigger_correlation_rule_id ? parseInt(formData.trigger_correlation_rule_id) : null,
                    actions_config: actions_config, // Вже розпарсений масив об'єктів
                };
                await onSave(dataToSave, initialData?.id);
            } catch (e) {
                // Помилка вже має бути встановлена в validate або onSave
                console.error("Error preparing data for save:", e)
            }
        }
    };

    return (
        <Dialog open={open} onClose={onClose} PaperProps={{ component: 'form', onSubmit: handleSubmit }} maxWidth="md" fullWidth>
            <DialogTitle>{initialData ? 'Редагувати Пайплайн Реагування' : 'Створити Новий Пайплайн'}</DialogTitle>
            <DialogContent>
                {formError && <Alert severity="error" sx={{ mb: 2 }}>{String(formError)}</Alert>}
                <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                        <TextField margin="dense" name="name" label="Назва Пайплайна" value={formData.name} onChange={handleChange} error={!!errors.name} helperText={errors.name} fullWidth disabled={isLoading}/>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                        <TextField margin="dense" name="trigger_correlation_rule_id" label="ID Правила-Тригера (опціонально)" type="number" value={formData.trigger_correlation_rule_id || ''} onChange={handleChange} error={!!errors.trigger_correlation_rule_id} helperText={errors.trigger_correlation_rule_id} fullWidth disabled={isLoading}/>
                        {/* TODO: Замінити на Select з доступними правилами */}
                    </Grid>
                    <Grid item xs={12}>
                        <TextField margin="dense" name="description" label="Опис" value={formData.description} onChange={handleChange} multiline rows={2} fullWidth disabled={isLoading}/>
                    </Grid>
                    <Grid item xs={12}>
                        <TextField
                            margin="dense" name="actions_config_json" label="Конфігурація Дій (JSON масив PipelineActionConfig)"
                            value={formData.actions_config_json} onChange={handleChange}
                            multiline rows={6} fullWidth variant="outlined"
                            error={!!errors.actions_config_json} helperText={errors.actions_config_json}
                            disabled={isLoading}
                            placeholder={'[\n  {\n    "action_id": 1,\n    "order": 1,\n    "action_params_template": {"ip_placeholder_from_offence": "{offence.matched_ioc_details.value}"}\n  }\n]'}
                        />
                        <Typography variant="caption">Кожен об'єкт має містити "action_id": (ID існуючої дії), "order": (порядок виконання), "action_params_template": (опціональний JSON об'єкт з параметрами)</Typography>
                    </Grid>
                    <Grid item xs={12}>
                        <FormControlLabel control={<Checkbox checked={formData.is_enabled} onChange={handleChange} name="is_enabled" />} label="Пайплайн активний" disabled={isLoading} />
                    </Grid>
                </Grid>
            </DialogContent>
            <DialogActions sx={{p:'0 24px 20px 24px'}}>
                <Button onClick={onClose} disabled={isLoading}>Скасувати</Button>
                <Button type="submit" variant="contained" disabled={isLoading}>
                    {isLoading ? <CircularProgress size={24} /> : (initialData ? 'Зберегти' : 'Створити')}
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default ResponsePipelineFormModal;