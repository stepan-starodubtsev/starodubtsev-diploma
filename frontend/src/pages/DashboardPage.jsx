// src/pages/DashboardPage.jsx
import React, { useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { Grid, Paper, Typography, Box, CircularProgress, Alert } from '@mui/material';

import correlationStore from '../stores/correlationStore';
import indicatorStore from '../stores/indicatorStore';
// import aptGroupStore from '../stores/aptGroupStore'; // Якщо потрібен для AptOffencesWidget для отримання імен

import OffencesSummaryWidget from '../components/dashboard/OffencesSummaryWidget';
import RecentOffencesWidget from '../components/dashboard/RecentOffencesWidget';
import TopIoCsWidget from '../components/dashboard/TopIoCsWidget'; // <--- Підключено
import AptOffencesWidget from '../components/dashboard/AptOffencesWidget'; // <--- Підключено
import IoCTypeDistributionWidget from '../components/dashboard/IoCTypeDistributionWidget';

const DashboardPage = observer(() => {
    useEffect(() => {
        // Завантажуємо дані, необхідні для всіх віджетів на дашборді
        // OffencesSummaryWidget та RecentOffencesWidget використовують correlationStore.offences
        if (correlationStore.offences.length === 0 && !correlationStore.isLoadingOffences) {
            correlationStore.fetchOffences(); // Завантажує останні офенси
        }
        // IoCTypeDistributionWidget використовує indicatorStore.iocs
        if (indicatorStore.iocs.length === 0 && !indicatorStore.isLoading) {
            indicatorStore.loadIoCs(); // Завантажує IoC
        }

        // Для TopIoCsWidget та AptOffencesWidget дані завантажуються всередині самих віджетів
        // або можна завантажувати їх тут, якщо вони використовуються в кількох місцях.
        // Наприклад, correlationStore.fetchTopTriggeredIoCs();
        // correlationStore.fetchOffencesByApt();
        // correlationStore.fetchOffencesSummary(); // Для детальної статистики за періодами

    }, []);

    const isLoading = correlationStore.isLoadingOffences || indicatorStore.isLoading;
    const error = correlationStore.error || indicatorStore.error; // Загальна помилка

    if (isLoading && correlationStore.offences.length === 0 && indicatorStore.iocs.length === 0) {
        return <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px"><CircularProgress /></Box>;
    }
    if (error && !isLoading) { // Показуємо помилку, тільки якщо не йде завантаження
        return <Alert severity="error" sx={{m:2}}>Помилка завантаження даних для дашборду: {String(error)}</Alert>;
    }

    return (
        <Box>
            <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
                Головний Дашборд Безпеки
            </Typography>
            <Grid container spacing={3}>
                <Grid item size={6}>
                    <OffencesSummaryWidget offences={correlationStore.offences} />
                </Grid>
                {/*<Grid item xs={12} md={6} lg={4}>*/}
                {/*    <IoCTypeDistributionWidget iocs={indicatorStore.iocs} />*/}
                {/*</Grid>*/}
                <Grid item xs={12} md={6} lg={4}>
                    <AptOffencesWidget />
                </Grid>
                <Grid item xs={12} lg={8}>
                    <RecentOffencesWidget
                        offences={correlationStore.offences.slice(0, 10)}
                        isLoading={correlationStore.isLoadingOffences}
                    />
                </Grid>
                <Grid item xs={12} lg={4}>
                    <TopIoCsWidget /> {/* Дані завантажуються всередині віджета */}
                </Grid>
            </Grid>
        </Box>
    );
});

export default DashboardPage;