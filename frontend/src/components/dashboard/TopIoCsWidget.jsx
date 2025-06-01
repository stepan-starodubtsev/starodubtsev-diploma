// src/components/dashboard/TopIoCsWidget.jsx
import React, { useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { Typography, Paper, Box, List, ListItem, ListItemText, Divider, CircularProgress, Alert, Chip, Tooltip } from '@mui/material';
import correlationStore from '../../stores/correlationStore';

const TopIoCsWidget = observer(() => {
    useEffect(() => {
        // Завантажуємо дані при монтуванні компонента
        correlationStore.fetchTopTriggeredIoCs(10, 7); // Топ-10 за останні 7 днів
    }, []); // Порожній масив залежностей для одноразового завантаження

    const { topTriggeredIoCs, isLoadingTopIoCs, error } = correlationStore; // Використовуємо error з correlationStore

    if (isLoadingTopIoCs) {
        return <Box display="flex" justifyContent="center" py={2}><CircularProgress size={24} /></Box>;
    }

    // Використовуємо загальне поле error зі стору, або можна створити errorTopIoCs
    if (error && topTriggeredIoCs.length === 0) { // Показуємо помилку, тільки якщо немає даних
        return <Alert severity="error" sx={{ mt: 1 }}>{String(error)}</Alert>;
    }

    return (
        <Paper elevation={2} sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
                Топ IoC за Спрацюваннями
            </Typography>
            {topTriggeredIoCs.length === 0 && !isLoadingTopIoCs ? (
                <Typography variant="body2">Немає даних про спрацювання IoC за обраний період.</Typography>
            ) : (
                <List dense disablePadding sx={{ maxHeight: 350, overflow: 'auto' }}>
                    {topTriggeredIoCs.map((ioc, index) => (
                        <React.Fragment key={`${ioc.ioc_value}-${ioc.ioc_type}-${index}`}>
                            <ListItem sx={{ py: 0.5 }}>
                                <ListItemText
                                    primary={
                                        <Tooltip title={ioc.ioc_value}>
                                            <Typography
                                                variant="body2"
                                                component="span"
                                                sx={{
                                                    wordBreak: 'break-all',
                                                    fontWeight: 500,
                                                    display: '-webkit-box',
                                                    WebkitLineClamp: 1, // Обмеження в 1 рядок
                                                    WebkitBoxOrient: 'vertical',
                                                    overflow: 'hidden',
                                                    textOverflow: 'ellipsis',
                                                }}
                                            >
                                                {ioc.ioc_value}
                                            </Typography>
                                        </Tooltip>
                                    }
                                    secondary={
                                        <>
                                            <Chip label={ioc.ioc_type || 'N/A'} size="small" sx={{ mr: 1 }} variant="outlined" />
                                            <Typography component="span" variant="caption" color="textSecondary">
                                                Спрацювань: {ioc.trigger_count}
                                            </Typography>
                                        </>
                                    }
                                />
                            </ListItem>
                            {index < topTriggeredIoCs.length - 1 && <Divider component="li" light />}
                        </React.Fragment>
                    ))}
                </List>
            )}
        </Paper>
    );
});

export default TopIoCsWidget;