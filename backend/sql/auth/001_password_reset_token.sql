-- Tabla para tokens de recuperación de contraseña (JWT / WhatsApp).
-- Ejecutar solo si migrate accounts.0003 no pudo crearla.

CREATE TABLE IF NOT EXISTS password_reset_token (
    id BIGSERIAL PRIMARY KEY,
    token VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ NULL,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS password_reset_token_token_idx ON password_reset_token (token);
CREATE INDEX IF NOT EXISTS password_reset_token_user_id_idx ON password_reset_token (user_id);
