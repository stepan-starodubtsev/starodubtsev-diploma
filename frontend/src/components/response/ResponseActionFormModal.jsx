// src/components/response/ResponseActionFormModal.jsx
import React, { useState, useEffect } from 'react';
import {
    Dialog, DialogActions, DialogContent, DialogTitle, TextField, Button,
    Select, MenuItem, FormControl, InputLabel, Checkbox, FormControlLabel,
    CircularProgress, Alert, Box, Typography
} from '@mui/material';
// Припускаємо, що ResponseActionTypeLabels є в constants.js
import { ResponseActionTypeEnum, ResponseActionTypeLabels } from '../../constants';

const initialFormState = {
    name: '',
    type: ResponseActionTypeEnum.BLOCK_IP, // Значення за замовчуванням
    description: '',
    is_enabled: true,
    default_params: '{}', // Зберігаємо як JSON рядок, парсимо перед відправкою
};

const ResponseActionFormModal = ({ open, onClose, onSave, initialData, isLoading, formError }) => {
    const [formData, setFormData] = useState(initialFormState);
    const [errors, setErrors] = useState({});

    useEffect(() => {
        if (open) {
            if (initialData) {
                setFormData({
                    name: initialData.name || '',
                    type: initialData.type?.value || initialData.type || ResponseActionTypeEnum.BLOCK_IP,
                    description: initialData.description || '',
                    is_enabled: initialData.is_enabled !== undefined ? initialData.is_enabled : true,
                    default_params: initialData.default_params ? JSON.stringify(initialData.default_params, null, 2) : '{}',
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
        if (!formData.name.trim()) tempErrors.name = "Назва дії є обов'язковою";
        if (!formData.type) tempErrors.type = "Тип дії є обов'язковим";
        try {
            JSON.parse(formData.default_params);
        } catch (e) {
            tempErrors.default_params = "Параметри за замовчуванням мають бути валідним JSON";
        }
        setErrors(tempErrors);
        return Object.keys(tempErrors).length === 0;
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        if (validate()) {
            try {
                const paramsParsed = JSON.parse(formData.default_params);
                const dataToSave = {
                    ...formData,
                    default_params: paramsParsed
                };
                await onSave(dataToSave, initialData?.id);
            } catch(e) {
                setErrors(prev => ({...prev, default_params: "Некоректний JSON у параметрах"}));
            }
        }
    };

    return (
        <Dialog open={open} onClose={onClose} PaperProps={{ component: 'form', onSubmit: handleSubmit }} maxWidth="sm" fullWidth>
            <DialogTitle>{initialData ? 'Редагувати Дію Реагування' : 'Створити Нову Дію Реагування'}</DialogTitle>
            <DialogContent>
                {formError && <Alert severity="error" sx={{ mb: 2 }}>{String(formError)}</Alert>}
                <TextField margin="dense" name="name" label="Назва Дії" value={formData.name} onChange={handleChange} error={!!errors.name} helperText={errors.name} fullWidth disabled={isLoading}/>

                <FormControl fullWidth margin="dense" variant="outlined" error={!!errors.type}>
                    <InputLabel id="response-action-type-label">Тип Дії</InputLabel>
                    <Select
                        labelId="response-action-type-label" name="type"
                        value={formData.type} onChange={handleChange} label="Тип Дії" disabled={isLoading}
                    >
                        {(ResponseActionTypeLabels || Object.entries(ResponseActionTypeEnum)).map(opt_or_entry => {
                            const value = Array.isArray(opt_or_entry) ? opt_or_entry[1].value : opt_or_entry.value; // Адаптовано для обох форматів
                            const label = Array.isArray(opt_or_entry) ? opt_or_entry[0] : opt_or_entry.label;
                            return <MenuItem key={value} value={value}>{label}</MenuItem>;
                        })}
                    </Select>
                    {errors.type && <Typography color="error" variant="caption" sx={{ml:2}}>{errors.type}</Typography>}
                </FormControl>

                <TextField margin="dense" name="description" label="Опис" value={formData.description} onChange={handleChange} multiline rows={2} fullWidth disabled={isLoading}/>

                <TextField
                    margin="dense" name="default_params" label="Параметри за замовчуванням (JSON)"
                    value={formData.default_params} onChange={handleChange}
                    multiline rows={4} fullWidth variant="outlined"
                    error={!!errors.default_params} helperText={errors.default_params}
                    disabled={isLoading}
                    placeholder={'{\n  "device_id": 1,\n  "list_name": "siem_blocked_ips"\n}'}
                />

                <FormControlLabel
                    control={<Checkbox checked={formData.is_enabled} onChange={handleChange} name="is_enabled" />}
                    label="Дія активна" sx={{mt:1}} disabled={isLoading}
                />
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

export default ResponseActionFormModal;