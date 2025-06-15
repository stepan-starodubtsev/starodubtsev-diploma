import React from 'react';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, IconButton, Box, Chip
} from '@mui/material';
import { Edit, Delete } from '@mui/icons-material';
import { observer } from 'mobx-react-lite';

const UserTable = observer(({ users, onEdit, onDelete }) => {
    const getRoleChipColor = (role) => {
        switch (role) {
            case 'admin':
                return 'error';
            case 'user':
                return 'info';
            default:
                return 'default';
        }
    };

    return (
        <TableContainer component={Paper}>
            <Table sx={{ minWidth: 650 }} aria-label="user table">
                <TableHead>
                    <TableRow>
                        <TableCell>ID</TableCell>
                        <TableCell>Ім'я користувача</TableCell>
                        <TableCell>Повне ім'я</TableCell>
                        <TableCell>Роль</TableCell>
                        <TableCell align="right">Дії</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {users.map((user) => (
                        <TableRow
                            key={user.id}
                            sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                        >
                            <TableCell component="th" scope="row">
                                {user.id}
                            </TableCell>
                            <TableCell>{user.username}</TableCell>
                            <TableCell>{user.full_name}</TableCell>
                            <TableCell>
                                <Chip
                                    label={user.role}
                                    color={getRoleChipColor(user.role)}
                                    size="small"
                                />
                            </TableCell>
                            <TableCell align="right">
                                <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                                    <IconButton onClick={() => onEdit(user)} color="primary">
                                        <Edit />
                                    </IconButton>
                                    <IconButton onClick={() => onDelete(user.id)} color="error">
                                        <Delete />
                                    </IconButton>
                                </Box>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
});

export default UserTable;