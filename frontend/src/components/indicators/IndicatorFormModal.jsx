// src/components/indicators/IndicatorFormModal.jsx
import React, {useEffect, useState} from 'react';
import {
    Alert,
    Autocomplete,
    Box,
    Button,
    Checkbox,
    Chip,
    CircularProgress,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    FormControl,
    FormControlLabel,
    InputLabel,
    MenuItem,
    Select,
    TextField,
    Typography
} from '@mui/material';
import {IoCTypeEnum} from '../../constants'; // Припускаємо, що IoCTypeEnum тут
// import aptGroupStore from '../../stores/aptGroupStore'; // Якщо потрібен список APT для вибору

// Для прикладу, список типів IoC для Select
const iocTypeOptions = Object.entries(IoCTypeEnum).map(([key, value]) => ({value, label: key.replace("_", " ")}));

const initialFormState = {
    value: '',
    type: IoCTypeEnum.IPV4_ADDR, // Значення за замовчуванням
    description: '',
    source_name: '',
    is_active: true,
    confidence: 75, // За замовчуванням
    tags: [],
    first_seen: null, // '' для TextField type="datetime-local"
    last_seen: null,  // '' для TextField type="datetime-local"
    attributed_apt_group_ids: [],
};

const IndicatorFormModal = ({
                                open,
                                onClose,
                                onSave,
                                initialData,
                                isLoading,
                                formError,
                                aptGroupStore,
                                sourceNames,
                                allPossibleTags
                            }) => { // Додано aptGroupStore
    const [formData, setFormData] = useState(initialFormState);
    const [errors, setErrors] = useState({});
    const [currentTag, setCurrentTag] = useState('');

    // Завантажуємо список APT груп для вибору, якщо потрібно
    useEffect(() => {
        if (open && aptGroupStore && aptGroupStore.aptGroups.length === 0 && !aptGroupStore.isLoading) {
            aptGroupStore.fetchAptGroups(); // Завантажуємо, якщо список порожній
        }
    }, [open, aptGroupStore]);


    useEffect(() => {
        if (initialData) {
            setFormData({
                value: initialData.value || '',
                type: initialData.type?.value || initialData.type || IoCTypeEnum.IPV4_ADDR,
                description: initialData.description || '',
                source_name: initialData.source_name || '',
                is_active: initialData.is_active !== undefined ? initialData.is_active : true,
                confidence: initialData.confidence !== null ? initialData.confidence : 75,
                tags: initialData.tags || [],
                first_seen: initialData.first_seen ? new Date(initialData.first_seen).toISOString().slice(0, 16) : '',
                last_seen: initialData.last_seen ? new Date(initialData.last_seen).toISOString().slice(0, 16) : '',
                attributed_apt_group_ids: initialData.attributed_apt_group_ids || [],
            });
        } else {
            setFormData(initialFormState);
        }
        setErrors({});
    }, [initialData, open]);

    const handleChange = (event) => {
        const {name, value, type, checked} = event.target;
        setFormData(prev => ({...prev, [name]: type === 'checkbox' ? checked : value}));
        if (errors[name]) setErrors(prev => ({...prev, [name]: ''}));
    };

    const handleAddTag = () => {
        if (currentTag.trim() && !formData.tags.includes(currentTag.trim())) {
            setFormData(prev => ({...prev, tags: [...prev.tags, currentTag.trim()]}));
            setCurrentTag('');
        }
    };
    const handleDeleteTag = (tagToDelete) => {
        setFormData(prev => ({...prev, tags: prev.tags.filter(tag => tag !== tagToDelete)}));
    };


    const validate = () => {
        const tempErrors = {};
        if (!formData.value.trim()) tempErrors.value = "Значення є обов'язковим";
        if (!formData.type) tempErrors.type = "Тип є обов'язковим";
        if (formData.confidence !== null && (formData.confidence < 0 || formData.confidence > 100)) {
            tempErrors.confidence = "Впевненість має бути від 0 до 100";
        }
        setErrors(tempErrors);
        return Object.keys(tempErrors).length === 0;
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        if (validate()) {
            const dataToSave = {
                ...formData,
                first_seen: formData.first_seen ? new Date(formData.first_seen).toISOString() : null,
                last_seen: formData.last_seen ? new Date(formData.last_seen).toISOString() : null,
            };
            // Упевнимося, що attributed_apt_group_ids - це список чисел
            dataToSave.attributed_apt_group_ids = (dataToSave.attributed_apt_group_ids || []).map(id => Number(id)).filter(id => !isNaN(id));

            await onSave(dataToSave, initialData?.ioc_id); // Передаємо ioc_id для оновлення
        }
    };

    const aptOptions = aptGroupStore ? aptGroupStore.aptGroups.map(apt => ({id: apt.id, name: apt.name})) : [];
    const selectedAptObjects = formData.attributed_apt_group_ids
        .map(id => aptOptions.find(opt => opt.id === id))
        .filter(Boolean);


    return (
        <Dialog open={open} onClose={onClose} PaperProps={{component: 'form', onSubmit: handleSubmit}} maxWidth="md"
                fullWidth>
            <DialogTitle>{initialData ? 'Редагувати Індикатор (IoC)' : 'Додати Новий Індикатор (IoC)'}</DialogTitle>
            <DialogContent>
                {formError && <Alert severity="error" sx={{mb: 2}}>{formError}</Alert>}
                <TextField margin="dense" name="value" label="Значення IoC" value={formData.value}
                           onChange={handleChange} error={!!errors.value} helperText={errors.value} fullWidth
                           disabled={isLoading}/>

                <FormControl fullWidth margin="dense" variant="outlined" error={!!errors.type}>
                    <InputLabel id="ioc-type-select-label">Тип IoC</InputLabel>
                    <Select labelId="ioc-type-select-label" name="type" value={formData.type} onChange={handleChange}
                            label="Тип IoC" disabled={isLoading}>
                        {iocTypeOptions.map(opt => <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>)}
                    </Select>
                    {errors.type && <Typography color="error" variant="caption" sx={{ml: 2}}>{errors.type}</Typography>}
                </FormControl>

                <TextField margin="dense" name="description" label="Опис" value={formData.description}
                           onChange={handleChange} multiline rows={2} fullWidth disabled={isLoading}/>
                <FormControl fullWidth variant="outlined">
                    <InputLabel id="source-name-select-label">Джерело</InputLabel>
                    <Select
                        labelId="source-name-select-label"
                        id="source-name-select"
                        name="source_name"
                        value={formData.source_name}
                        onChange={handleChange}
                        label="Джерело"
                    >
                        <MenuItem value="">
                            <em>Не вибрано</em>
                        </MenuItem>
                        {/* Рендеримо список отриманих джерел */}
                        {sourceNames.map((source) => (
                            <MenuItem
                                key={source.id || source.name} // Використовуємо унікальний id або name для ключа
                                value={source.name} // Значенням елемента буде рядок source.name
                            >
                                {source.name} {/* А текстом для відображення - також source.name */}
                            </MenuItem>
                        ))}

                    </Select>
                </FormControl>
                <TextField margin="dense" name="confidence" label="Впевненість (0-100)" type="number"
                           value={formData.confidence} onChange={handleChange} error={!!errors.confidence}
                           helperText={errors.confidence} fullWidth disabled={isLoading}/>

                <Autocomplete
                    multiple
                    freeSolo
                    id="form-tags-autocomplete"
                    value={formData.tags || []}
                    onChange={(event, newValue) => {
                        setFormData(prev => ({
                            ...prev,
                            tags: newValue
                        }));
                    }}
                    options={allPossibleTags || []}

                    renderTags={(tagValue, getTagProps) =>
                        tagValue.map((option, index) => (
                            <Chip
                                variant="outlined"
                                label={option}
                                {...getTagProps({ index })}
                            />
                        ))
                    }

                    // Як виглядає поле вводу
                    renderInput={(params) => (
                        <TextField
                            {...params}
                            variant="outlined"
                            margin="normal"
                            label="Теги"
                            placeholder="Додайте або виберіть теги"
                            disabled={isLoading}
                        />
                    )}
                />

                {aptGroupStore && // Показуємо вибір APT тільки якщо aptGroupStore передано
                    <Autocomplete
                        multiple
                        id="attributed-apt-group-ids"
                        options={aptOptions}
                        getOptionLabel={(option) => `${option.name} (ID: ${option.id})`}
                        value={selectedAptObjects} // Використовуємо об'єкти для відображення
                        onChange={(event, newValueObjects) => {
                            setFormData(prev => ({
                                ...prev,
                                attributed_apt_group_ids: newValueObjects.map(obj => obj.id)
                            }));
                        }}
                        isOptionEqualToValue={(option, value) => option.id === value.id}
                        renderInput={(params) => (
                            <TextField
                                {...params}
                                variant="outlined"
                                label="Прив'язані APT Угруповання"
                                placeholder="Виберіть APT"
                                margin="dense"
                                disabled={isLoading}
                            />
                        )}
                        renderTags={(value, getTagProps) =>
                            value.map((option, index) => (
                                <Chip variant="outlined" label={`${option.name}`} {...getTagProps({index})} />
                            ))
                        }
                    />
                }

                <TextField margin="dense" name="first_seen" label="Вперше Помічено (опціонально)" type="datetime-local"
                           value={formData.first_seen} onChange={handleChange} fullWidth
                           InputLabelProps={{shrink: true}} sx={{mt: 1}} disabled={isLoading}/>
                <TextField margin="dense" name="last_seen" label="Остання Активність (опціонально)"
                           type="datetime-local" value={formData.last_seen} onChange={handleChange} fullWidth
                           InputLabelProps={{shrink: true}} disabled={isLoading}/>

                <FormControlLabel
                    control={<Checkbox checked={formData.is_active} onChange={handleChange} name="is_active"
                                       color="primary" disabled={isLoading}/>}
                    label="Індикатор активний" sx={{mt: 1}}
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

export default IndicatorFormModal;