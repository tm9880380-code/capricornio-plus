/* Punto de entrada reservado para utilidades compartidas del frontend. */
"use strict";
window.Capricornio = Object.freeze({
  async request(url, options = {}) {
    const response = await fetch(url, {
      credentials: "same-origin",
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) }
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "No fue posible completar la solicitud.");
    }
    return data;
  }
});
