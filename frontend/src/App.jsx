// src/App.js
import React, {useState, useMemo, createContext} from 'react';
import {Box, CssBaseline, ThemeProvider} from '@mui/material';
import {BrowserRouter, Routes, Route, Navigate} from 'react-router-dom'; // Додано Navigate

import {getAppTheme} from './theme'; // Наш файл з темою

// Компоненти макету
import Header from './components/layout/Header';
import DevicesPage from "./pages/DevicesPage.jsx";
import IoCSourcesPage from "./pages/IoCSourcesPage.jsx";
import APTGroupsPage from "./pages/APTGroupsPage.jsx";
import IndicatorsPage from "./pages/IndicatorsPage.jsx";
import CorrelationRulesPage from "./pages/CorrelationRulesPage.jsx";
import OffencesPage from "./pages/OffencesPage.jsx";
import ResponsePage from "./pages/ResponsePage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import LoginPage from "./pages/LoginPage.jsx"; // <--- НОВИЙ ХЕДЕР

// Приклади сторінок (створи їх у src/pages/)
// const ProfilePage = () => <div>Профіль Користувача</div>; // Заглушка
import ProtectedRoute from './components/auth/ProtectedRoute'; // Імпорт ProtectedRoute
import authStore from './stores/authStore';
import UsersPage from "./pages/UsersPage.jsx";
import {observer} from "mobx-react-lite";

export const ColorModeContext = createContext({
    toggleColorMode: () => {
    }
});

const App = observer(() => {
    const [mode, setMode] = useState('dark'); // <--- Змінено на 'light' за замовчуванням

    const colorMode = useMemo(
        () => ({
            toggleColorMode: () => {
                setMode((prevMode) => (prevMode === 'light' ? 'dark' : 'light'));
            },
        }),
        [],
    );

    const theme = useMemo(() => getAppTheme(mode), [mode]);

    return (
        <ColorModeContext.Provider value={colorMode}>
            <ThemeProvider theme={theme}>
                <CssBaseline/>
                <BrowserRouter>
                    <Box sx={{display: 'flex', flexDirection: 'column', height: '100vh'}}> {/* Змінено на column */}
                        {authStore.isAuthenticated && <Header />}

                        <Box
                            component="main"
                            sx={{
                                flexGrow: 1,
                                p: 3, // Використовуємо p для padding з теми
                                overflowY: 'auto',
                                backgroundColor: theme.palette.background.default
                            }}
                        >
                            <Routes>
                                <Route path="/login" element={<LoginPage />} />

                                <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
                                <Route path="/devices" element={<ProtectedRoute><DevicesPage /></ProtectedRoute>} />
                                <Route path="/indicators" element={<ProtectedRoute><IndicatorsPage /></ProtectedRoute>} />
                                <Route path="/correlation" element={<ProtectedRoute><CorrelationRulesPage /></ProtectedRoute>} />
                                <Route path="/offences" element={<ProtectedRoute><OffencesPage /></ProtectedRoute>} />
                                <Route path="/response" element={<ProtectedRoute><ResponsePage /></ProtectedRoute>} />
                                <Route path="/apt-groups" element={<ProtectedRoute><APTGroupsPage /></ProtectedRoute>} />
                                <Route path="/ioc-sources" element={<ProtectedRoute><IoCSourcesPage /></ProtectedRoute>} />
                                <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />

                                {/* Маршрут тільки для адмінів */}
                                <Route path="/users" element={
                                    <ProtectedRoute adminOnly={true}>
                                        <UsersPage />
                                    </ProtectedRoute>
                                } />

                                <Route path="*" element={<Navigate to="/" replace />} />
                            </Routes>
                        </Box>
                    </Box>
                </BrowserRouter>
            </ThemeProvider>
        </ColorModeContext.Provider>
    );
});

export default App;

// Не забудь імпортувати Box з @mui/material, якщо ще не зроблено
// import { Box } from '@mui/material'; (має бути вже через ThemeProvider/CssBaseline)