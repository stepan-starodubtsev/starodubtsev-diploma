// frontend/src/components/auth/ProtectedRoute.jsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { observer } from 'mobx-react-lite';
import authStore from '../../stores/authStore';

const ProtectedRoute = observer(({ children, adminOnly = false }) => {
    const location = useLocation();

    if (!authStore.isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (adminOnly && !authStore.isAdmin) {
        // Користувач залогінений, але не адмін. Перенаправляємо на головну.
        return <Navigate to="/" replace />;
    }

    return children;
});

export default ProtectedRoute;