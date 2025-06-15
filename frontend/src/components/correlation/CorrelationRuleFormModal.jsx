// src/components/correlation/CorrelationRuleFormModal.jsx
import React, {useState, useEffect} from 'react';
import {
    Dialog, DialogActions, DialogContent, DialogTitle, TextField, Button,
    Select, MenuItem, FormControl, InputLabel, Checkbox, FormControlLabel,
    CircularProgress, Alert, Box, Typography, Grid, Autocomplete, Chip
} from '@mui/material';
import {
    CorrelationRuleTypeEnum, EventFieldToMatchTypeEnum, IoCTypeToMatchEnum, OffenceSeverityEnum,
    CorrelationRuleTypeLabels, EventFieldToMatchLabels, OffenceSeverityLabels // Потрібно додати їх в constants.js
} from '../../constants'; // Або з correlation/schemas

const iocTypeOptions = Object.entries(IoCTypeToMatchEnum).map(([key, value]) => ({
    value,
    label: key.replace("_", " ")
}));
// Event source types - це можуть бути твої event_category або event_type з CommonEventSchema
const eventSourceTypeOptions = [
    {value: "netflow", label: "NetFlow/Flow"},
    {value: "syslog_firewall", label: "Syslog (Firewall)"},
    {value: "syslog_auth", label: "Syslog (Authentication)"},
    {value: "syslog_system", label: "Syslog (System)"},
    {value: "authentication", label: "Authentication Event (Generic)"},
    // ... додай інші
];


const initialFormState = {
    name: '',
    description: '',
    is_enabled: true,
    rule_type: CorrelationRuleTypeEnum.IOC_MATCH_IP, // За замовчуванням
    event_source_type: [],
    event_field_to_match: null,
    ioc_type_to_match: null,
    ioc_tags_match: [],
    ioc_min_confidence: null,
    threshold_count: null,
    threshold_time_window_minutes: null,
    aggregation_fields: [],
    generated_offence_title_template: '',
    generated_offence_severity: OffenceSeverityEnum.MEDIUM,
};

const CorrelationRuleFormModal = ({open, onClose, onSave, initialData, isLoading, formError, allPossibleTags}) => {
    const [formData, setFormData] = useState(initialFormState);
    const [errors, setErrors] = useState({});


    useEffect(() => {
        if (open) {
            if (initialData) {
                setFormData({
                    name: initialData.name || '',
                    description: initialData.description || '',
                    is_enabled: initialData.is_enabled !== undefined ? initialData.is_enabled : true,
                    rule_type: initialData.rule_type?.value || initialData.rule_type || CorrelationRuleTypeEnum.IOC_MATCH_IP,
                    event_source_type: initialData.event_source_type || [],
                    event_field_to_match: initialData.event_field_to_match?.value || initialData.event_field_to_match || null,
                    ioc_type_to_match: initialData.ioc_type_to_match?.value || initialData.ioc_type_to_match || null,
                    ioc_tags_match: initialData.ioc_tags_match || [],
                    ioc_min_confidence: initialData.ioc_min_confidence !== null ? initialData.ioc_min_confidence : null,
                    threshold_count: initialData.threshold_count !== null ? initialData.threshold_count : null,
                    threshold_time_window_minutes: initialData.threshold_time_window_minutes !== null ? initialData.threshold_time_window_minutes : null,
                    aggregation_fields: (initialData.aggregation_fields || []).map(f => f.value || f), // Якщо aggregation_fields зберігаються як Enum
                    generated_offence_title_template: initialData.generated_offence_title_template || '',
                    generated_offence_severity: initialData.generated_offence_severity?.value || initialData.generated_offence_severity || OffenceSeverityEnum.MEDIUM,
                });
            } else {
                setFormData(initialFormState);
            }
            setErrors({});
        }
    }, [initialData, open]);

    const handleChange = (event) => {
        const {name, value, type, checked} = event.target;
        setFormData(prev => ({...prev, [name]: type === 'checkbox' ? checked : value}));
        if (errors[name]) setErrors(prev => ({...prev, [name]: ''}));
    };

    const handleMultiSelectChange = (name, newValue) => {
        setFormData(prev => ({...prev, [name]: newValue}));
    };


    const validate = () => {
        // ... (базова валідація, можна розширити залежно від rule_type)
        const tempErrors = {};
        if (!formData.name.trim()) tempErrors.name = "Назва є обов'язковою";
        if (!formData.rule_type) tempErrors.rule_type = "Тип правила є обов'язковим";
        if (!formData.generated_offence_title_template.trim()) tempErrors.generated_offence_title_template = "Шаблон заголовка офенса є обов'язковим";
        if (!formData.generated_offence_severity) tempErrors.generated_offence_severity = "Серйозність офенса є обов'язковою";

        if (formData.rule_type === CorrelationRuleTypeEnum.IOC_MATCH_IP) {
            if (!formData.event_field_to_match) tempErrors.event_field_to_match = "Поле події є обов'язковим для IoC правил";
            if (!formData.ioc_type_to_match) tempErrors.ioc_type_to_match = "Тип IoC є обов'язковим для IoC правил";
        } else if (formData.rule_type === CorrelationRuleTypeEnum.THRESHOLD_LOGIN_FAILURES || formData.rule_type === CorrelationRuleTypeEnum.THRESHOLD_DATA_EXFILTRATION) {
            if (formData.threshold_count === null || formData.threshold_count <= 0) tempErrors.threshold_count = "Поріг має бути > 0";
            if (formData.threshold_time_window_minutes === null || formData.threshold_time_window_minutes <= 0) tempErrors.threshold_time_window_minutes = "Часове вікно має бути > 0";
            if (!formData.aggregation_fields || formData.aggregation_fields.length === 0) tempErrors.aggregation_fields = "Поля агрегації є обов'язковими для порогових правил";
        }
        setErrors(tempErrors);
        return Object.keys(tempErrors).length === 0;
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        if (validate()) {
            const dataToSave = {...formData};
            // Очистимо непотрібні поля залежно від rule_type перед відправкою
            if (dataToSave.rule_type !== CorrelationRuleTypeEnum.IOC_MATCH_IP) {
                dataToSave.event_field_to_match = null;
                dataToSave.ioc_type_to_match = null;
                dataToSave.ioc_tags_match = [];
                dataToSave.ioc_min_confidence = null;
            }
            if (dataToSave.rule_type !== CorrelationRuleTypeEnum.THRESHOLD_LOGIN_FAILURES &&
                dataToSave.rule_type !== CorrelationRuleTypeEnum.THRESHOLD_DATA_EXFILTRATION) {
                dataToSave.threshold_count = null;
                dataToSave.threshold_time_window_minutes = null;
                dataToSave.aggregation_fields = [];
            }
            await onSave(dataToSave, initialData?.id);
        }
    };

    return (
        <Dialog open={open} onClose={onClose} PaperProps={{component: 'form', onSubmit: handleSubmit}} maxWidth="lg"
                fullWidth>
            <DialogTitle>{initialData ? 'Редагувати Правило Кореляції' : 'Додати Нове Правило Кореляції'}</DialogTitle>
            <DialogContent>
                {formError && <Alert severity="error" sx={{mb: 2}}>{formError}</Alert>}
                <Grid container spacing={2}>
                    <Grid item size={6}>
                        <TextField margin="dense" name="name" label="Назва Правила" value={formData.name}
                                   onChange={handleChange} error={!!errors.name} helperText={errors.name} fullWidth
                                   disabled={isLoading}/>
                    </Grid>
                    <Grid item size={6}>
                        <FormControl fullWidth margin="dense" variant="outlined" error={!!errors.rule_type}>
                            <InputLabel id="rule-type-label">Тип Правила</InputLabel>
                            <Select labelId="rule-type-label" name="rule_type" value={formData.rule_type}
                                    onChange={handleChange} label="Тип Правила" disabled={isLoading}>
                                {CorrelationRuleTypeLabels.map(opt => <MenuItem key={opt.value}
                                                                                value={opt.value}>{opt.label}</MenuItem>)}
                            </Select>
                            {errors.rule_type && <Typography color="error" variant="caption"
                                                             sx={{ml: 2}}>{errors.rule_type}</Typography>}
                        </FormControl>
                    </Grid>
                    <Grid item size={12}>
                        <TextField margin="dense" name="description" label="Опис" value={formData.description}
                                   onChange={handleChange} multiline rows={2} fullWidth disabled={isLoading}/>
                    </Grid>

                    <Grid item size={12}> <Typography variant="subtitle1" sx={{mt: 1}}>Конфігурація
                        Спрацювання</Typography> </Grid>

                    <Grid item size={5}>
                        <Autocomplete
                            multiple
                            options={eventSourceTypeOptions.map(opt => opt.value)} // Або використовуй eventSourceTypeLabels
                            getOptionLabel={(option) => eventSourceTypeOptions.find(o => o.value === option)?.label || option}
                            value={formData.event_source_type}
                            onChange={(event, newValue) => handleMultiSelectChange('event_source_type', newValue)}
                            renderTags={(value, getTagProps) =>
                                value.map((option, index) => (
                                    <Chip variant="outlined"
                                          label={eventSourceTypeOptions.find(o => o.value === option)?.label || option} {...getTagProps({index})} />
                                ))
                            }
                            renderInput={(params) => (
                                <TextField {...params} variant="outlined" label="Типи Подій Джерела"
                                           placeholder="Виберіть типи" margin="dense" disabled={isLoading}/>
                            )}
                        />
                    </Grid>

                    {/* Поля для IOC_MATCH_IP */}
                    {formData.rule_type === CorrelationRuleTypeEnum.IOC_MATCH_IP && (
                        <>
                            <Grid item size={4}>
                                <FormControl fullWidth margin="dense" variant="outlined"
                                             error={!!errors.event_field_to_match}>
                                    <InputLabel>Поле Події для Зіставлення</InputLabel>
                                    <Select name="event_field_to_match" value={formData.event_field_to_match || ''}
                                            onChange={handleChange} label="Поле Події для Зіставлення"
                                            disabled={isLoading}>
                                        <MenuItem value=""><em>Не вибрано</em></MenuItem>
                                        {EventFieldToMatchLabels.filter(f => f.value.includes("_IP")).map(opt =>
                                            <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>)}
                                    </Select>
                                    {errors.event_field_to_match && <Typography color="error" variant="caption"
                                                                                sx={{ml: 2}}>{errors.event_field_to_match}</Typography>}
                                </FormControl>
                            </Grid>
                            <Grid item size={3}>
                                <FormControl fullWidth margin="dense" variant="outlined"
                                             error={!!errors.ioc_type_to_match}>
                                    <InputLabel>Тип IoC для Зіставлення</InputLabel>
                                    <Select name="ioc_type_to_match" value={formData.ioc_type_to_match || ''}
                                            onChange={handleChange} label="Тип IoC для Зіставлення"
                                            disabled={isLoading}>
                                        <MenuItem value=""><em>Не вибрано</em></MenuItem>
                                        {iocTypeOptions.filter(t => t.value.includes("-addr")).map(opt => <MenuItem
                                            key={opt.value} value={opt.value}>{opt.label}</MenuItem>)}
                                    </Select>
                                    {errors.ioc_type_to_match && <Typography color="error" variant="caption"
                                                                             sx={{ml: 2}}>{errors.ioc_type_to_match}</Typography>}
                                </FormControl>
                            </Grid>
                            <Grid item size={6}>
                                <Autocomplete
                                    multiple
                                    freeSolo
                                    value={formData.ioc_tags_match || []}
                                    onChange={(event, newValue) => {
                                        setFormData(prev => ({
                                            ...prev,
                                            ioc_tags_match: newValue
                                        }));
                                    }}
                                    options={allPossibleTags || []}
                                    renderTags={(value, getTagProps) =>
                                        value.map((option, index) => (
                                            <Chip variant="outlined" label={option} {...getTagProps({index})} />
                                        ))
                                    }
                                    renderInput={(params) => (
                                        <TextField
                                            {...params}
                                            variant="outlined"
                                            margin="normal"
                                            label="Теги IoC для Зіставлення (AND)"
                                            placeholder="Додайте або виберіть теги"
                                            disabled={isLoading}
                                        />
                                    )}
                                />
                            </Grid>
                        </>
                    )}

                    {/* Поля для THRESHOLD правил */}
                    {(formData.rule_type === CorrelationRuleTypeEnum.THRESHOLD_LOGIN_FAILURES || formData.rule_type === CorrelationRuleTypeEnum.THRESHOLD_DATA_EXFILTRATION) && (
                        <>
                            <Grid item size={4}>
                                <TextField margin="dense" name="threshold_count" label="Поріг (N або сума байт)"
                                           type="number" value={formData.threshold_count || ''} onChange={handleChange}
                                           error={!!errors.threshold_count} helperText={errors.threshold_count}
                                           fullWidth disabled={isLoading}/>
                            </Grid>
                            <Grid item size={4}>
                                <TextField margin="dense" name="threshold_time_window_minutes"
                                           label="Часове Вікно (хвилин)" type="number"
                                           value={formData.threshold_time_window_minutes || ''} onChange={handleChange}
                                           error={!!errors.threshold_time_window_minutes}
                                           helperText={errors.threshold_time_window_minutes} fullWidth
                                           disabled={isLoading}/>
                            </Grid>
                            <Grid item size={4}>
                                <Autocomplete
                                    multiple
                                    options={Object.values(EventFieldToMatchTypeEnum)}
                                    getOptionLabel={(optionValue) => EventFieldToMatchLabels.find(l => l.value === optionValue)?.label || optionValue}
                                    value={formData.aggregation_fields}
                                    onChange={(event, newValue) => handleMultiSelectChange('aggregation_fields', newValue)}
                                    renderTags={(value, getTagProps) =>
                                        value.map((optionValue, index) => (
                                            <Chip variant="outlined"
                                                  label={EventFieldToMatchLabels.find(l => l.value === optionValue)?.label || optionValue} {...getTagProps({index})} />
                                        ))
                                    }
                                    renderInput={(params) => (
                                        <TextField {...params} variant="outlined" label="Поля Агрегації"
                                                   placeholder="Виберіть поля" margin="dense"
                                                   error={!!errors.aggregation_fields}
                                                   helperText={errors.aggregation_fields} disabled={isLoading}/>
                                    )}
                                />
                            </Grid>
                        </>
                    )}

                    <Grid item xs={12}> <Typography variant="subtitle1" sx={{mt: 2}}>Генерація Офенса</Typography>
                    </Grid>
                    <Grid item xs={12} md={8}>
                        <TextField margin="dense" name="generated_offence_title_template"
                                   label="Шаблон Заголовка Офенса" value={formData.generated_offence_title_template}
                                   onChange={handleChange} error={!!errors.generated_offence_title_template}
                                   helperText={errors.generated_offence_title_template} fullWidth disabled={isLoading}/>
                    </Grid>
                    <Grid item size={4}>
                        <FormControl fullWidth margin="dense" variant="outlined"
                                     error={!!errors.generated_offence_severity}>
                            <InputLabel>Серйозність Офенса</InputLabel>
                            <Select name="generated_offence_severity" value={formData.generated_offence_severity}
                                    onChange={handleChange} label="Серйозність Офенса" disabled={isLoading}>
                                {OffenceSeverityLabels.map(opt => <MenuItem key={opt.value}
                                                                            value={opt.value}>{opt.label}</MenuItem>)}
                            </Select>
                            {errors.generated_offence_severity && <Typography color="error" variant="caption"
                                                                              sx={{ml: 2}}>{errors.generated_offence_severity}</Typography>}
                        </FormControl>
                    </Grid>

                    <Grid item xs={12}>
                        <FormControlLabel control={<Checkbox checked={formData.is_enabled} onChange={handleChange}
                                                             name="is_enabled"/>} label="Правило активне"
                                          disabled={isLoading}/>
                    </Grid>
                </Grid>
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

export default CorrelationRuleFormModal;