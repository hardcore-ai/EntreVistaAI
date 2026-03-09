"use client";

import { useEffect, useState } from "react";
import { getCampaigns, getEvaluations } from "@/lib/api";
import type { Campaign, Evaluation } from "@/lib/types";
import { Users, CheckCircle, Clock, TrendingUp } from "lucide-react";

export default function DashboardHome() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [pendingEvals, setPendingEvals] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getCampaigns(), getEvaluations({ status: "pending_review" })])
      .then(([c, e]) => { setCampaigns(c); setPendingEvals(e); })
      .finally(() => setLoading(false));
  }, []);

  const totalCandidates = campaigns.reduce((s, c) => s + (c.stats?.total || 0), 0);
  const totalCompleted = campaigns.reduce((s, c) => s + (c.stats?.completed || 0), 0);
  const avgCompletion = campaigns.length
    ? Math.round(campaigns.reduce((s, c) => s + (c.stats?.completion_rate || 0), 0) / campaigns.length)
    : 0;

  const stats = [
    { label: "Candidatos totales", value: totalCandidates, icon: Users, color: "bg-blue-100 text-blue-600" },
    { label: "Completaron entrevista", value: totalCompleted, icon: CheckCircle, color: "bg-green-100 text-green-600" },
    { label: "Pendientes de revisión", value: pendingEvals.length, icon: Clock, color: "bg-yellow-100 text-yellow-600" },
    { label: "Tasa de completación", value: `${avgCompletion}%`, icon: TrendingUp, color: "bg-purple-100 text-purple-600" },
  ];

  if (loading) return <div className="p-8 text-gray-400">Cargando...</div>;

  return (
    <div className="p-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Resumen</h2>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((s) => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-4">
            <div className={`rounded-lg p-2 ${s.color}`}>
              <s.icon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-2xl font-bold">{s.value}</p>
              <p className="text-xs text-gray-500">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Pending review queue preview */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-5 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">Cola de revisión pendiente</h3>
          <a href="/dashboard/candidates" className="text-sm text-brand-600 hover:underline">Ver todo</a>
        </div>
        {pendingEvals.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No hay evaluaciones pendientes de revisión.</div>
        ) : (
          <ul className="divide-y divide-gray-50">
            {pendingEvals.slice(0, 5).map((ev) => (
              <li key={ev.id} className="px-5 py-3 flex items-center justify-between hover:bg-gray-50">
                <div>
                  <p className="font-medium text-sm">{ev.candidate_name || "Candidato"}</p>
                  <p className="text-xs text-gray-400">{ev.campaign_title}</p>
                </div>
                <div className="flex items-center gap-3">
                  {ev.overall_score !== null && (
                    <span className="text-sm font-semibold text-gray-700">{ev.overall_score.toFixed(0)}/100</span>
                  )}
                  <RecommendationBadge rec={ev.ai_recommendation} />
                  <a
                    href={`/dashboard/candidates/${ev.session_id}`}
                    className="text-xs bg-brand-600 text-white px-3 py-1 rounded-full hover:bg-brand-700"
                  >
                    Revisar
                  </a>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function RecommendationBadge({ rec }: { rec: string | null }) {
  const map: Record<string, { label: string; className: string }> = {
    highly_recommended: { label: "Muy recomendado", className: "bg-green-100 text-green-700" },
    recommended: { label: "Recomendado", className: "bg-blue-100 text-blue-700" },
    needs_review: { label: "Revisar", className: "bg-yellow-100 text-yellow-700" },
    not_recommended: { label: "No recomendado", className: "bg-red-100 text-red-700" },
  };
  if (!rec) return null;
  const { label, className } = map[rec] || { label: rec, className: "bg-gray-100 text-gray-700" };
  return <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${className}`}>{label}</span>;
}
