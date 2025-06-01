// src/components/dashboard/OffencesSummaryWidget.jsx
import React from 'react';
import { Typography, Paper, Box, Grid } from '@mui/material';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline'; // High
import WarningAmberIcon from '@mui/icons-material/WarningAmber';   // Medium
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'; // Low
import ReportProblemIcon from '@mui/icons-material/ReportProblem'; // Critical

// Потрібно імпортувати OffenceSeverityEnum з constants.js
import { OffenceSeverityEnum } from '../../constants';

const OffencesSummaryWidget = ({ offences }) => {
    // Логіка для підрахунку офенсів за періодами та серйозністю
    // Цю логіку краще реалізувати на бекенді та отримувати через API,
    // або розраховувати в MobX сторі, якщо обсяг даних невеликий.

    // Приклад простого підрахунку завантажених офенсів за серйозністю
    const countBySeverity = (severity) => offences.filter(off => (off.severity?.value || off.severity) === severity).length;

    const criticalCount = countBySeverity(OffenceSeverityEnum.CRITICAL);
    const highCount = countBySeverity(OffenceSeverityEnum.HIGH);
    const mediumCount = countBySeverity(OffenceSeverityEnum.MEDIUM);
    const lowCount = countBySeverity(OffenceSeverityEnum.LOW);

    // Для періодів (24h, 7d, 30d) потрібна буде фільтрація за `detected_at`
    // та, ймовірно, окремі API запити або більш складний стан.

    return (
        <Box>
            <Typography variant="h6" gutterBottom>Огляд Офенсів</Typography>
            <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                    <Paper elevation={2} sx={{p: 2, textAlign: 'center', backgroundColor: (theme) => theme.palette.error.dark, color: 'white'}}>
                        <ReportProblemIcon sx={{fontSize: 40}}/>
                        <Typography variant="h4">{criticalCount}</Typography>
                        <Typography variant="caption">Критичні</Typography>
                    </Paper>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Paper elevation={2} sx={{p: 2, textAlign: 'center', backgroundColor: (theme) => theme.palette.error.main}}>
                        <ErrorOutlineIcon sx={{fontSize: 40}}/>
                        <Typography variant="h4">{highCount}</Typography>
                        <Typography variant="caption">Високої серйозності</Typography>
                    </Paper>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Paper elevation={2} sx={{p: 2, textAlign: 'center', backgroundColor: (theme) => theme.palette.warning.main}}>
                        <WarningAmberIcon sx={{fontSize: 40}}/>
                        <Typography variant="h4">{mediumCount}</Typography>
                        <Typography variant="caption">Середньої серйозності</Typography>
                    </Paper>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Paper elevation={2} sx={{p: 2, textAlign: 'center', backgroundColor: (theme) => theme.palette.info.main}}>
                        <InfoOutlinedIcon sx={{fontSize: 40}}/>
                        <Typography variant="h4">{lowCount}</Typography>
                        <Typography variant="caption">Низької серйозності</Typography>
                    </Paper>
                </Grid>
            </Grid>
            <Typography variant="body2" sx={{mt: 2}}>*Показано кількість з поточного завантаженого списку.</Typography>
            <Typography variant="body2" sx={{mt: 1}}>*Для статистики за періодами потрібні окремі API.</Typography>
        </Box>
    );
};

export default OffencesSummaryWidget;