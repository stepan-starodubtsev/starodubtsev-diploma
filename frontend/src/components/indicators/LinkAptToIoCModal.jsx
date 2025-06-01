// src/components/indicators/LinkAptToIoCModal.jsx
import React, { useState, useEffect } from 'react';
import {
    Dialog, DialogActions, DialogContent, DialogTitle, Button,
    FormControl, InputLabel, Select, MenuItem, CircularProgress, Alert,
    Autocomplete, TextField, Chip, Box
} from '@mui/material';
// import aptGroupStore from '../../stores/aptGroupStore'; // Або передавати список APT як props

const LinkAptToIoCModal = ({ open, onClose, onLink, ioc, aptGroupStore, isLoading, error }) => {
    // aptGroupStore має містити aptGroups: [{id, name}, ...]
    const [selectedAptIds, setSelectedAptIds] = useState([]);

    useEffect(() => {
        if (open && aptGroupStore && aptGroupStore.aptGroups.length === 0 && !aptGroupStore.isLoading) {
            aptGroupStore.fetchAptGroups();
        }
        // Встановлюємо поточні прив'язані APT ID, коли модалка відкривається для конкретного IoC
        if (open && ioc && ioc.attributed_apt_group_ids) {
            setSelectedAptIds(ioc.attributed_apt_group_ids);
        } else if (open) {
            setSelectedAptIds([]); // Якщо новий IoC або немає даних
        }
    }, [open, aptGroupStore, ioc]);

    const handleSubmit = () => {
        // Логіка для відправки декількох зв'язків (якщо потрібно)
        // Або, якщо API linkIoCToApt приймає один apt_group_id,
        // то ця модалка має дозволяти вибір одного APT для прив'язки за раз.
        // Поточний API indicators/api.py має ендпоінт /link-apt/{apt_group_id}
        // Тобто, ми прив'язуємо по одному APT за раз.
        // Ця модалка може бути для вибору ОДНОГО APT для прив'язки.

        // Якщо ми хочемо оновити ВЕСЬ список attributed_apt_group_ids через цю модалку,
        // то onLink має приймати ioc.ioc_id та новий список selectedAptIds,
        // а сервіс/API IoC має мати метод для оновлення цього поля (наприклад, через PUT /iocs/{ioc_id}).
        // Наразі, припустимо, onLink викликається для кожного вибраного ID, або один раз з масивом.
        // Для простоти, нехай onLink приймає лише один aptGroupId.
        // Користувач має вибрати один APT зі списку.

        // Якщо selectedAptIds тут - це один ID:
        if (selectedAptIds.length === 1) { // Припускаємо, що це ID, а не об'єкт
            onLink(ioc.ioc_id, selectedAptIds[0]);
        } else if (selectedAptIds.length > 1) {
            // Якщо дозволено множинний вибір і onLink може обробити масив
            // Або потрібно викликати onLink для кожного ID
            alert("Будь ласка, виберіть одне APT угруповання для прив'язки за раз через цей інтерфейс, або реалізуйте множинне зв'язування.");
        } else {
            alert("Будь ласка, виберіть APT угруповання.");
        }
    };

    const aptOptions = aptGroupStore ? aptGroupStore.aptGroups.map(apt => ({ id: apt.id, name: apt.name })) : [];
    // Знаходимо об'єкти APT, які відповідають вибраним ID, для відображення в Autocomplete
    const valueForAutocomplete = selectedAptIds
        .map(id => aptOptions.find(opt => opt.id === id))
        .filter(Boolean); // Видаляємо undefined, якщо ID не знайдено в options

    return (
        <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
            <DialogTitle>Прив'язати IoC "{ioc?.value}" до APT</DialogTitle>
            <DialogContent>
                {error && <Alert severity="error" sx={{ mb: 2 }}>{String(error)}</Alert>}
                {aptGroupStore?.isLoading && <CircularProgress />}
                {!aptGroupStore?.isLoading && aptOptions.length === 0 && (
                    <Alert severity="warning">Список APT угруповань порожній. Спочатку додайте APT.</Alert>
                )}
                {!aptGroupStore?.isLoading && aptOptions.length > 0 && (
                    <Autocomplete
                        multiple // Дозволяє вибрати кілька APT
                        id="link-apt-select"
                        options={aptOptions}
                        getOptionLabel={(option) => `${option.name} (ID: ${option.id})`}
                        value={valueForAutocomplete} // Має бути масив об'єктів {id, name}
                        onChange={(event, newValueObjects) => {
                            setSelectedAptIds(newValueObjects.map(obj => obj.id));
                        }}
                        isOptionEqualToValue={(option, value) => option.id === value.id}
                        renderInput={(params) => (
                            <TextField
                                {...params}
                                variant="outlined"
                                label="Виберіть APT Угруповання"
                                placeholder="Почніть вводити назву..."
                                margin="normal"
                            />
                        )}
                        renderTags={(value, getTagProps) =>
                            value.map((option, index) => (
                                <Chip variant="outlined" label={option.name} {...getTagProps({ index })} />
                            ))
                        }
                        sx={{mt:1}}
                    />
                )}
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Скасувати</Button>
                {/* Ця кнопка має викликати onLink для кожного вибраного ID,
            або onLink має приймати масив ID. Поточний API /link-apt/ очікує один ID APT.
            Для простоти, зробимо так, що користувач вибирає один APT. Змінимо Autocomplete на single.
        */}
                {/* Якщо Autocomplete буде single:
        <Button onClick={() => { if (selectedAptIds.length > 0) onLink(ioc.ioc_id, selectedAptIds[0]);}} color="primary" disabled={isLoading || selectedAptIds.length === 0}>
          Прив'язати
        </Button>
        */}
                {/* Якщо ми хочемо оновити ВЕСЬ список attributed_apt_group_ids IoC: */}
                <Button onClick={() => onLink(ioc.ioc_id, selectedAptIds)} color="primary" disabled={isLoading}>
                    Оновити зв'язки APT
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default LinkAptToIoCModal;