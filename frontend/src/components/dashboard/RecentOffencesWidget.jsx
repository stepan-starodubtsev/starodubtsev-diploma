// src/components/dashboard/RecentOffencesWidget.jsx
import React from 'react';
import { List, ListItem, ListItemText, Typography, Divider, Paper, Chip, Box, CircularProgress } from '@mui/material';
import { format } from 'date-fns';
import { OffenceSeverityLabels, OffenceStatusLabels } from '../../constants'; // Припускаємо

const RecentOffencesWidget = ({ offences, isLoading }) => {
    const getSeverityChipColor = (severityValue) => { /* ... як в OffenceTable ... */
        switch (severityValue) {
            case 'low': return 'info';
            case 'medium': return 'warning';
            case 'high': return 'error';
            case 'critical': return 'error';
            default: return 'default';
        }
    };


    if (isLoading && !offences.length) {
        return <CircularProgress />;
    }

    return (
        <Box>
            <Typography variant="h6" gutterBottom>Останні Офенси</Typography>
            {offences.length === 0 ? (
                <Typography variant="body2">Немає виявлених офенсів.</Typography>
            ) : (
                <Paper variant="outlined">
                    <List dense disablePadding>
                        {offences.map((offence, index) => (
                            <React.Fragment key={offence.id}>
                                <ListItem alignItems="flex-start">
                                    <ListItemText
                                        primary={
                                            <Typography variant="subtitle2" component="span" sx={{ fontWeight: 'bold' }}>
                                                {offence.title}
                                            </Typography>
                                        }
                                        secondary={
                                            <>
                                                <Chip
                                                    label={(OffenceSeverityLabels.find(s => s.value === (offence.severity?.value || offence.severity))?.label || offence.severity || '').toUpperCase()}
                                                    color={getSeverityChipColor(offence.severity?.value || offence.severity)}
                                                    size="small" sx={{mr: 1}}
                                                />
                                                <Chip
                                                    label={OffenceStatusLabels.find(s => s.value === (offence.status?.value || offence.status))?.label || offence.status}
                                                    size="small" sx={{mr: 1}} variant="outlined"
                                                />
                                                <Typography component="span" variant="caption" color="textSecondary">
                                                    {offence.detected_at ? format(new Date(offence.detected_at), 'yyyy-MM-dd HH:mm') : 'N/A'}
                                                    {offence.correlation_rule_id ? ` (Правило: ${offence.correlation_rule_id})` : ''}
                                                </Typography>
                                                {offence.description &&
                                                    <Typography component="div" variant="body2" color="text.secondary" sx={{mt: 0.5, whiteSpace: 'pre-line'}}>
                                                        {offence.description.length > 150 ? offence.description.substring(0, 147) + "..." : offence.description}
                                                    </Typography>
                                                }
                                            </>
                                        }
                                    />
                                    {/* Тут можна додати кнопку для переходу до деталей офенса */}
                                </ListItem>
                                {index < offences.length - 1 && <Divider component="li" />}
                            </React.Fragment>
                        ))}
                    </List>
                </Paper>
            )}
        </Box>
    );
};

export default RecentOffencesWidget;