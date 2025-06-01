// src/components/apt_groups/APTGroupFormModal.jsx
import React, {useState, useEffect} from 'react';
import {
    Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
    TextField, Button, Select, MenuItem, FormControl, InputLabel, Chip, Box,
    CircularProgress, Alert, Typography
} from '@mui/material';
// Імпортуємо Enum-и зі схем або констант
import {APTGroupMotivationsEnum, APTGroupSophisticationEnum} from '../../constants.js'; // Або з constants.js

const motivationOptions = Object.entries(APTGroupMotivationsEnum).map(([key, value]) => ({value, label: key}));
const sophisticationOptions = Object.entries(APTGroupSophisticationEnum).map(([key, value]) => ({value, label: key}));


const initialFormState = {
    name: '',
    aliases: [], // Масив рядків
    description: '',
    sophistication: APTGroupSophisticationEnum.UNKNOWN.value,
    primary_motivation: APTGroupMotivationsEnum.UNKNOWN.value,
    target_sectors: [], // Масив рядків
    country_of_origin: '',
    first_observed: null, // Будемо використовувати TextField type="datetime-local"
    last_observed: null,
    references: [], // Масив рядків (URL)
};

const APTGroupFormModal = ({open, onClose, onSave, initialData, isLoading, formError}) => {
    const [formData, setFormData] = useState(initialFormState);
    const [errors, setErrors] = useState({});

    // Для полів, що є масивами рядків (aliases, target_sectors, references)
    const [currentAlias, setCurrentAlias] = useState('');
    const [currentSector, setCurrentSector] = useState('');
    const [currentReference, setCurrentReference] = useState('');

    useEffect(() => {
        if (initialData) {
            setFormData({
                name: initialData.name || '',
                aliases: initialData.aliases || [],
                description: initialData.description || '',
                sophistication: initialData.sophistication?.value || initialData.sophistication || APTGroupSophisticationEnum.UNKNOWN.value,
                primary_motivation: initialData.primary_motivation?.value || initialData.primary_motivation || APTGroupMotivationsEnum.UNKNOWN.value,
                target_sectors: initialData.target_sectors || [],
                country_of_origin: initialData.country_of_origin || '',
                first_observed: initialData.first_observed ? new Date(initialData.first_observed).toISOString().slice(0, 16) : '',
                last_observed: initialData.last_observed ? new Date(initialData.last_observed).toISOString().slice(0, 16) : '',
                references: initialData.references || [],
            });
        } else {
            setFormData(initialFormState);
        }
        setErrors({});
    }, [initialData, open]);

    const handleChange = (event) => {
        const {name, value} = event.target;
        setFormData(prev => ({...prev, [name]: value}));
        if (errors[name]) setErrors(prev => ({...prev, [name]: ''}));
    };

    const handleArrayFieldAdd = (field, currentFieldValue, setCurrentFieldValue) => {
        if (currentFieldValue.trim() === '') return;
        setFormData(prev => ({
            ...prev,
            [field]: [...(prev[field] || []), currentFieldValue.trim()]
        }));
        setCurrentFieldValue('');
    };

    const handleArrayFieldDelete = (field, valueToDelete) => {
        setFormData(prev => ({
            ...prev,
            [field]: (prev[field] || []).filter(item => item !== valueToDelete)
        }));
    };


    const validate = () => {
        const tempErrors = {};
        if (!formData.name.trim()) tempErrors.name = "Назва є обов'язковою";
        // ... інші валідації за потреби ...
        setErrors(tempErrors);
        return Object.keys(tempErrors).length === 0;
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        if (validate()) {
            const dataToSave = {
                ...formData,
                // Конвертуємо дати назад в ISO формат або залишаємо як є, якщо API приймає datetime-local
                first_observed: formData.first_observed ? new Date(formData.first_observed).toISOString() : null,
                last_observed: formData.last_observed ? new Date(formData.last_observed).toISOString() : null,
                // references мають бути HttpUrl, але ми передаємо рядки, Pydantic на бекенді має це обробити
            };
            // Видаляємо порожні масиви, якщо вони не потрібні (або API їх обробить)
            if (dataToSave.aliases && dataToSave.aliases.length === 0) delete dataToSave.aliases;
            if (dataToSave.target_sectors && dataToSave.target_sectors.length === 0) delete dataToSave.target_sectors;
            if (dataToSave.references && dataToSave.references.length === 0) delete dataToSave.references;

            await onSave(dataToSave, initialData?.id);
        }
    };

    return (
        <Dialog open={open} onClose={onClose} PaperProps={{component: 'form', onSubmit: handleSubmit}} maxWidth="md"
                fullWidth>
            <DialogTitle>{initialData ? 'Редагувати APT Угруповання' : 'Додати Нове APT Угруповання'}</DialogTitle>
            <DialogContent>
                {formError && <Alert severity="error" sx={{mb: 2}}>{formError}</Alert>}
                <TextField margin="dense" name="name" label="Назва Угруповання" value={formData.name}
                           onChange={handleChange} error={!!errors.name} helperText={errors.name} fullWidth
                           disabled={isLoading}/>

                <Box my={2}>
                    <Typography variant="subtitle2">Псевдоніми</Typography>
                    {formData.aliases.map((alias, index) => (
                        <Chip key={index} label={alias} onDelete={() => handleArrayFieldDelete('aliases', alias)}
                              sx={{mr: 0.5, mb: 0.5}}/>
                    ))}
                    <Box display="flex" alignItems="center" mt={1}>
                        <TextField size="small" label="Додати псевдонім" value={currentAlias}
                                   onChange={(e) => setCurrentAlias(e.target.value)} sx={{mr: 1}} disabled={isLoading}/>
                        <Button size="small"
                                onClick={() => handleArrayFieldAdd('aliases', currentAlias, setCurrentAlias)}
                                variant="outlined" disabled={isLoading}>Додати</Button>
                    </Box>
                </Box>

                <TextField margin="dense" name="description" label="Опис" value={formData.description}
                           onChange={handleChange} multiline rows={3} fullWidth disabled={isLoading}/>

                <FormControl fullWidth margin="dense" variant="outlined">
                    <InputLabel id="apt-sophistication-label">Рівень Складності</InputLabel>
                    <Select labelId="apt-sophistication-label" name="sophistication" value={formData.sophistication}
                            onChange={handleChange} label="Рівень Складності" disabled={isLoading}>
                        {sophisticationOptions.map(opt => <MenuItem key={opt.value}
                                                                    value={opt.value}>{opt.label}</MenuItem>)}
                    </Select>
                </FormControl>

                <FormControl fullWidth margin="dense" variant="outlined">
                    <InputLabel id="apt-motivation-label">Основна Мотивація</InputLabel>
                    <Select labelId="apt-motivation-label" name="primary_motivation" value={formData.primary_motivation}
                            onChange={handleChange} label="Основна Мотивація" disabled={isLoading}>
                        {motivationOptions.map(opt => <MenuItem key={opt.value}
                                                                value={opt.value}>{opt.label}</MenuItem>)}
                    </Select>
                </FormControl>

                <Box my={2}>
                    <Typography variant="subtitle2">Цільові Сектори</Typography>
                    {formData.target_sectors.map((sector, index) => (
                        <Chip key={index} label={sector}
                              onDelete={() => handleArrayFieldDelete('target_sectors', sector)}
                              sx={{mr: 0.5, mb: 0.5}}/>
                    ))}
                    <Box display="flex" alignItems="center" mt={1}>
                        <TextField size="small" label="Додати сектор" value={currentSector}
                                   onChange={(e) => setCurrentSector(e.target.value)} sx={{mr: 1}}
                                   disabled={isLoading}/>
                        <Button size="small"
                                onClick={() => handleArrayFieldAdd('target_sectors', currentSector, setCurrentSector)}
                                variant="outlined" disabled={isLoading}>Додати</Button>
                    </Box>
                </Box>

                <TextField margin="dense" name="country_of_origin" label="Країна Походження (ймовірна)"
                           value={formData.country_of_origin} onChange={handleChange} fullWidth disabled={isLoading}/>

                <TextField margin="dense" name="first_observed" label="Вперше Помічено" type="datetime-local"
                           value={formData.first_observed} onChange={handleChange} fullWidth
                           InputLabelProps={{shrink: true}} disabled={isLoading}/>
                <TextField margin="dense" name="last_observed" label="Остання Активність" type="datetime-local"
                           value={formData.last_observed} onChange={handleChange} fullWidth
                           InputLabelProps={{shrink: true}} disabled={isLoading}/>

                <Box my={2}>
                    <Typography variant="subtitle2">Посилання на Джерела</Typography>
                    {formData.references.map((ref, index) => (
                        <Chip key={index} label={ref.length > 30 ? ref.substring(0, 27) + '...' : ref}
                              onDelete={() => handleArrayFieldDelete('references', ref)} sx={{mr: 0.5, mb: 0.5}}/>
                    ))}
                    <Box display="flex" alignItems="center" mt={1}>
                        <TextField size="small" label="Додати URL" type="url" value={currentReference}
                                   onChange={(e) => setCurrentReference(e.target.value)} sx={{mr: 1}} fullWidth
                                   disabled={isLoading}/>
                        <Button size="small"
                                onClick={() => handleArrayFieldAdd('references', currentReference, setCurrentReference)}
                                variant="outlined" disabled={isLoading}>Додати</Button>
                    </Box>
                </Box>

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

export default APTGroupFormModal;