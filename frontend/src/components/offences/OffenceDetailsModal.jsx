// src/components/offences/OffenceDetailsModal.jsx
import React, { useState, useEffect } from 'react';
import {
    Dialog, DialogActions, DialogContent, DialogTitle, Button, Typography, Box, Grid,
    Select, MenuItem, FormControl, InputLabel, TextField, CircularProgress, Divider
} from '@mui/material';
import { OffenceStatusEnum, OffenceSeverityEnum, OffenceStatusLabels, OffenceSeverityLabels } from '../../constants';
import { format } from 'date-fns';

const OffenceDetailsModal = ({ open, onClose, offence, onUpdate, isLoading }) => {
    const [status, setStatus] = useState('');
    const [severity, setSeverity] = useState(''); // Додано для можливості зміни серйозності
    const [notes, setNotes] = useState('');

    useEffect(() => {
        if (offence) {
            setStatus(offence.status?.value || offence.status || OffenceStatusEnum.NEW);
            setSeverity(offence.severity?.value || offence.severity || OffenceSeverityEnum.MEDIUM);
            setNotes(offence.notes || '');
        }
    }, [offence]);

    if (!offence) return null;

    const handleSave = () => {
        onUpdate(offence.id, status, notes, severity); // Передаємо і серйозність
    };

    const renderJsonDetails = (title, data) => {
        if (!data) return null;
        let displayData = data;
        if (typeof data === 'string') {
            try { displayData = JSON.parse(data); } catch (e) { /* залишити як рядок */ }
        }
        return (
            <Box mt={2}>
                <Typography variant="subtitle1" gutterBottom>{title}:</Typography>
                <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', backgroundColor: '#f5f5f5', padding: '10px', borderRadius: '4px' }}>
                {JSON.stringify(displayData, null, 2)}
            </pre>
            </Box>
        );
    }

    return (
        <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth scroll="paper">
            <DialogTitle>Деталі Офенса ID: {offence.id} - {offence.title}</DialogTitle>
            <DialogContent dividers>
                <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                        <Typography variant="subtitle2">Серйозність:</Typography>
                        <FormControl fullWidth margin="dense" size="small">
                            <Select value={severity} onChange={(e) => setSeverity(e.target.value)}>
                                {OffenceSeverityLabels.map(s => <MenuItem key={s.value} value={s.value}>{s.label}</MenuItem>)}
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                        <Typography variant="subtitle2">Статус:</Typography>
                        <FormControl fullWidth margin="dense" size="small">
                            <Select value={status} onChange={(e) => setStatus(e.target.value)}>
                                {OffenceStatusLabels.map(s => <MenuItem key={s.value} value={s.value}>{s.label}</MenuItem>)}
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid item xs={12}>
                        <Typography variant="subtitle2">Опис:</Typography>
                        <Typography variant="body2" gutterBottom>{offence.description || 'N/A'}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                        <Typography variant="subtitle2">ID Правила Кореляції:</Typography>
                        <Typography variant="body2">{offence.correlation_rule_id}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                        <Typography variant="subtitle2">Час Виявлення:</Typography>
                        <Typography variant="body2">
                            {offence.detected_at ? format(new Date(offence.detected_at), 'yyyy-MM-dd HH:mm:ss') : 'N/A'}
                        </Typography>
                    </Grid>
                    <Grid item xs={12}>
                        <TextField
                            margin="dense"
                            label="Нотатки Аналітика"
                            type="text"
                            fullWidth
                            multiline
                            rows={4}
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            variant="outlined"
                        />
                    </Grid>

                    {offence.triggering_event_summary && (
                        <Grid item xs={12}>
                            {renderJsonDetails("Деталі Події, що Спричинила Офенс", offence.triggering_event_summary)}
                        </Grid>
                    )}
                    {offence.matched_ioc_details && (
                        <Grid item xs={12}>
                            {renderJsonDetails("Деталі IoC, що Спрацював", offence.matched_ioc_details)}
                        </Grid>
                    )}
                    {offence.attributed_apt_group_ids && offence.attributed_apt_group_ids.length > 0 && (
                        <Grid item xs={12}>
                            <Typography variant="subtitle2">Пов'язані APT ID:</Typography>
                            <Typography variant="body2">{offence.attributed_apt_group_ids.join(', ')}</Typography>
                        </Grid>
                    )}
                </Grid>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Закрити</Button>
                <Button onClick={handleSave} color="primary" variant="contained" disabled={isLoading}>
                    {isLoading ? <CircularProgress size={24} /> : 'Оновити Статус/Нотатки'}
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default OffenceDetailsModal;