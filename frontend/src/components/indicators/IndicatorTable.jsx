// src/components/indicators/IndicatorTable.jsx
import React from 'react';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
    IconButton, Tooltip, Box, Chip, TablePagination, Typography
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import LinkIcon from '@mui/icons-material/Link'; // Для зв'язування з APT
import { format } from 'date-fns'; // Для форматування дати

const IndicatorTable = ({
                            iocs, onEdit, onDelete, onLinkApt,
                            page, rowsPerPage, count, onPageChange, onRowsPerPageChange
                        }) => {

    return (
        <Box>
            <TableContainer component={Paper} elevation={2}>
                <Table sx={{ minWidth: 650 }} aria-label="indicators table">
                    <TableHead sx={{ backgroundColor: (theme) => theme.palette.action.hover }}>
                        <TableRow>
                            <TableCell sx={{minWidth: 150}}>Значення</TableCell>
                            <TableCell>Тип</TableCell>
                            <TableCell sx={{minWidth: 200}}>Опис</TableCell>
                            <TableCell>Джерело</TableCell>
                            <TableCell>Активний</TableCell>
                            <TableCell>Впевненість</TableCell>
                            <TableCell>Теги</TableCell>
                            <TableCell>APT IDs</TableCell>
                            <TableCell sx={{minWidth: 150}}>Останнє Оновлення (SIEM)</TableCell>
                            <TableCell align="center">Дії</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {iocs.length > 0 ? iocs.map((ioc) => (
                            <TableRow key={ioc.ioc_id} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                <TableCell component="th" scope="row">
                                    <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>{ioc.value}</Typography>
                                </TableCell>
                                <TableCell><Chip label={ioc.type?.value || ioc.type} size="small" /></TableCell>
                                <TableCell>{ioc.description || 'N/A'}</TableCell>
                                <TableCell>{ioc.source_name || 'N/A'}</TableCell>
                                <TableCell>
                                    <Chip label={ioc.is_active ? 'Так' : 'Ні'} color={ioc.is_active ? 'success' : 'default'} size="small" />
                                </TableCell>
                                <TableCell align="center">{ioc.confidence !== null ? `${ioc.confidence}%` : 'N/A'}</TableCell>
                                <TableCell>
                                    {(ioc.tags || []).map(tag => <Chip key={tag} label={tag} size="small" sx={{mr:0.5, mb:0.5}}/>)}
                                </TableCell>
                                <TableCell>
                                    {(ioc.attributed_apt_group_ids || []).join(', ') || 'N/A'}
                                </TableCell>
                                <TableCell>
                                    {ioc.updated_at_siem ? format(new Date(ioc.updated_at_siem), 'yyyy-MM-dd HH:mm') : 'N/A'}
                                </TableCell>
                                <TableCell align="center">
                                    <Tooltip title="Прив'язати до APT">
                                        <IconButton size="small" onClick={() => onLinkApt(ioc)} color="secondary">
                                            <LinkIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Редагувати">
                                        <IconButton size="small" onClick={() => onEdit(ioc)} color="primary">
                                            <EditIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Видалити">
                                        <IconButton size="small" onClick={() => onDelete(ioc.ioc_id)} color="error">
                                            <DeleteIcon />
                                        </IconButton>
                                    </Tooltip>
                                </TableCell>
                            </TableRow>
                        )) : (
                            <TableRow>
                                <TableCell colSpan={10} align="center">
                                    Немає даних про індикатори
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
            <TablePagination
                rowsPerPageOptions={[5, 10, 25, 50, 100]}
                component="div"
                count={count} // Загальна кількість записів
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={onPageChange} // Функція з батьківського компонента/стору
                onRowsPerPageChange={onRowsPerPageChange} // Функція з батьківського компонента/стору
                labelRowsPerPage="Рядків на сторінці:"
            />
        </Box>
    );
};

export default IndicatorTable;