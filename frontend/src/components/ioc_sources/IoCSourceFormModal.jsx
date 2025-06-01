// src/components/ioc_sources/IoCSourceFormModal.jsx
import React, {useState, useEffect} from 'react';
import {
    Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
    TextField, Button, Select, MenuItem, FormControl, InputLabel, Checkbox, FormControlLabel,
    CircularProgress, Alert
} from '@mui/material';
import {IoCSourceTypeEnum} from '../../constants.js';


const initialFormState = {
    name: '',
    type: IoCSourceTypeEnum.INTERNAL.value, // Значення за замовчуванням
    url: '',
    description: '',
    is_enabled: true,
};

const IoCSourceFormModal = ({open, onClose, onSave, initialData, isLoading, formError}) => {
    const [formData, setFormData] = useState(initialFormState);
    const [errors, setErrors] = useState({});

    useEffect(() => {
        if (initialData) {
            setFormData({
                name: initialData.name || '',
                type: initialData.type?.value || initialData.type || IoCSourceTypeEnum.INTERNAL.value,
                url: initialData.url || '',
                description: initialData.description || '',
                is_enabled: initialData.is_enabled !== undefined ? initialData.is_enabled : true,
            });
        } else {
            setFormData(initialFormState);
        }
        setErrors({}); // Скидаємо помилки при відкритті/зміні даних
    }, [initialData, open]);

    const handleChange = (event) => {
        const {name, value, type, checked} = event.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value,
        }));
        if (errors[name]) {
            setErrors(prev => ({...prev, [name]: ''}));
        }
    };

    const validate = () => {
        const tempErrors = {};
        if (!formData.name.trim()) tempErrors.name = "Назва є обов'язковою";
        if (!formData.type) tempErrors.type = "Тип є обов'язковим";
        // URL може бути опціональним, але якщо вказано, має бути валідним (MUI TextField type="url" робить базову перевірку)
        // if (formData.url && !formData.url.startsWith('http')) tempErrors.url = "Некоректний URL";
        setErrors(tempErrors);
        return Object.keys(tempErrors).length === 0;
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        if (validate()) {
            const dataToSave = {...formData};
            // Переконуємося, що URL або null, або не порожній рядок, якщо він опціональний у схемі
            if (dataToSave.url === '') dataToSave.url = null;

            await onSave(dataToSave, initialData?.id);
        }
    };

    return (
        <Dialog open={open} onClose={onClose} PaperProps={{component: 'form', onSubmit: handleSubmit}} maxWidth="sm"
                fullWidth>
            <DialogTitle>{initialData ? 'Редагувати Джерело IoC' : 'Додати Нове Джерело IoC'}</DialogTitle>
            <DialogContent>
                <DialogContentText sx={{mb: 2}}>
                    {initialData ? 'Внесіть зміни та збережіть.' : 'Заповніть інформацію про нове джерело індикаторів.'}
                </DialogContentText>
                {formError && <Alert severity="error" sx={{mb: 2}}>{formError}</Alert>}
                <TextField
                    autoFocus
                    margin="dense" name="name" label="Назва Джерела" type="text" fullWidth variant="outlined"
                    value={formData.name} onChange={handleChange} error={!!errors.name} helperText={errors.name}
                    disabled={isLoading}
                />
                <FormControl fullWidth margin="dense" variant="outlined" error={!!errors.type}>
                    <InputLabel id="ioc-source-type-label">Тип Джерела</InputLabel>
                    <Select
                        labelId="ioc-source-type-label"
                        name="type"
                        value={formData.type} // formData.type має зберігати значення типу "misp", "opencti"
                        onChange={handleChange}
                        label="Тип Джерела"
                    >
                        {/* Генеруємо MenuItem з об'єкта IoCSourceTypeEnum */}
                        {Object.entries(IoCSourceTypeEnum).map(([key, value]) => (
                            <MenuItem key={value} value={value}>
                                {key} {/* Або якась більш дружня назва, якщо є мапінг */}
                            </MenuItem>
                        ))}
                    </Select>
                    {errors.type && <Typography color="error" variant="caption" sx={{ml: 2}}>{errors.type}</Typography>}
                </FormControl>
                <TextField
                    margin="dense" name="url" label="URL (опціонально)" type="url" fullWidth variant="outlined"
                    value={formData.url} onChange={handleChange} error={!!errors.url} helperText={errors.url}
                    disabled={isLoading}
                />
                <TextField
                    margin="dense" name="description" label="Опис (опціонально)" type="text" fullWidth multiline
                    rows={3} variant="outlined"
                    value={formData.description} onChange={handleChange} disabled={isLoading}
                />
                <FormControlLabel
                    control={<Checkbox checked={formData.is_enabled} onChange={handleChange} name="is_enabled"
                                       color="primary" disabled={isLoading}/>}
                    label="Джерело активне" sx={{mt: 1}}
                />
            </DialogContent>
            <DialogActions sx={{p: '0 24px 20px 24px'}}>
                <Button onClick={onClose} disabled={isLoading}>Скасувати</Button>
                <Button type="submit" variant="contained" disabled={isLoading}>
                    {isLoading ? <CircularProgress size={24}/> : (initialData ? 'Зберегти' : 'Створити')}
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default IoCSourceFormModal;