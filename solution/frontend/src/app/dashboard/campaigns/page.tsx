"use client";

import { useEffect, useState } from "react";
import { getCampaigns, createCampaign } from "@/lib/api";
import type { Campaign } from "@/lib/types";
import { Plus, Link, Pause, CheckCircle } from "lucide-react";

const BOT_USERNAME = process.env.NEXT_PUBLIC_BOT_USERNAME || "EntrevistaAIBot";

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    getCampaigns().then(setCampaigns).finally(() => setLoading(false));
  }, []);

  function telegramLink(token: string) {
    return `https://t.me/${BOT_USERNAME}?start=${token}`;
  }

  function statusBadge(status: string) {
    const map: Record<string, string> = {
      active: "bg-green-100 text-green-700",
      paused: "bg-yellow-100 text-yellow-700",
      closed: "bg-gray-100 text-gray-500",
    };
    const label: Record<string, string> = { active: "Activa", paused: "Pausada", closed: "Cerrada" };
    return (
      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${map[status] || "bg-gray-100"}`}>
        {label[status] || status}
      </span>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Campañas</h2>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-700"
        >
          <Plus className="w-4 h-4" /> Nueva campaña
        </button>
      </div>

      {loading ? (
        <div className="text-gray-400">Cargando...</div>
      ) : campaigns.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg">No hay campañas todavía.</p>
          <p className="text-sm">Crea tu primera campaña para empezar a recibir candidatos.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {campaigns.map((c) => (
            <div key={c.id} className="bg-white border border-gray-200 rounded-xl p-5">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-gray-900">{c.title}</h3>
                    {statusBadge(c.status)}
                  </div>
                  <p className="text-sm text-gray-500 line-clamp-2">{c.role_description || "Sin descripción"}</p>
                </div>
                <a
                  href={`/dashboard/campaigns/${c.id}`}
                  className="text-sm text-brand-600 hover:underline ml-4 shrink-0"
                >
                  Ver detalle
                </a>
              </div>

              {/* Stats row */}
              <div className="mt-4 grid grid-cols-4 gap-3">
                {[
                  { label: "Total", value: c.stats?.total || 0 },
                  { label: "Completaron", value: c.stats?.completed || 0 },
                  { label: "Abandonaron", value: c.stats?.abandoned || 0 },
                  { label: "Completación", value: `${c.stats?.completion_rate || 0}%` },
                ].map((s) => (
                  <div key={s.label} className="bg-gray-50 rounded-lg p-3 text-center">
                    <p className="text-lg font-bold text-gray-900">{s.value}</p>
                    <p className="text-xs text-gray-400">{s.label}</p>
                  </div>
                ))}
              </div>

              {/* Telegram link */}
              <div className="mt-3 flex items-center gap-2">
                <Link className="w-3 h-3 text-gray-400" />
                <a
                  href={telegramLink(c.telegram_link_token)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-brand-600 hover:underline truncate"
                >
                  {telegramLink(c.telegram_link_token)}
                </a>
                <button
                  onClick={() => navigator.clipboard.writeText(telegramLink(c.telegram_link_token))}
                  className="text-xs text-gray-400 hover:text-gray-600 ml-auto shrink-0"
                >
                  Copiar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <CreateCampaignModal
          onClose={() => setShowCreate(false)}
          onCreated={(c) => { setCampaigns((prev) => [c, ...prev]); setShowCreate(false); }}
        />
      )}
    </div>
  );
}

function CreateCampaignModal({ onClose, onCreated }: { onClose: () => void; onCreated: (c: Campaign) => void }) {
  const [form, setForm] = useState({
    title: "",
    role_description: "",
    knowledge_base: "",
    competencies: [
      { name: "Orientación al cliente", weight: 0.3, description: "Capacidad de atender y resolver necesidades del cliente con empatía" },
      { name: "Comunicación", weight: 0.3, description: "Claridad, escucha activa y adaptación del mensaje" },
      { name: "Resolución de problemas", weight: 0.4, description: "Capacidad de analizar situaciones y proponer soluciones efectivas" },
    ],
  });
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const campaign = await createCampaign(form);
      onCreated(campaign);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b">
          <h3 className="text-xl font-bold">Nueva campaña</h3>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Título del puesto *</label>
            <input
              type="text"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Ej: Agente de Servicio al Cliente"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Descripción del puesto</label>
            <textarea
              value={form.role_description}
              onChange={(e) => setForm((f) => ({ ...f, role_description: e.target.value }))}
              rows={3}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Describe el puesto, responsabilidades y perfil buscado..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Base de conocimiento (FAQ para el agente)</label>
            <textarea
              value={form.knowledge_base}
              onChange={(e) => setForm((f) => ({ ...f, knowledge_base: e.target.value }))}
              rows={4}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Preguntas frecuentes que el agente puede responder. Ej: Horario laboral, modalidad de trabajo, beneficios básicos..."
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg font-medium hover:bg-gray-50">
              Cancelar
            </button>
            <button type="submit" disabled={saving} className="flex-1 bg-brand-600 text-white py-2 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-60">
              {saving ? "Creando..." : "Crear campaña"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
