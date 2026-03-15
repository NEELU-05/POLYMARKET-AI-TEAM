"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { api } from "@/services/api";

interface EdgeBucket {
  name: string;
  wins: number;
  losses: number;
}

const EMPTY_BUCKETS: EdgeBucket[] = [
  { name: "0-5%", wins: 0, losses: 0 },
  { name: "5-10%", wins: 0, losses: 0 },
  { name: "10-15%", wins: 0, losses: 0 },
  { name: "15-20%", wins: 0, losses: 0 },
  { name: "20%+", wins: 0, losses: 0 },
];

export default function EdgeHistogram() {
  const [data, setData] = useState<EdgeBucket[]>(EMPTY_BUCKETS);

  useEffect(() => {
    api.getTradesSummary()
      .then((summary) => {
        if (summary.edge_distribution?.length > 0) {
          setData(summary.edge_distribution);
        }
      })
      .catch(() => {});
  }, []);

  const hasData = data.some((b) => b.wins + b.losses > 0);

  return (
    <div className="card h-full flex flex-col min-h-[300px]">
      <h3 className="mb-4 text-base font-semibold text-slate-200">Edge Distribution & Outcomes</h3>
      {!hasData ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-500 text-sm">No closed trades yet</p>
        </div>
      ) : (
        <div className="flex-1 w-full mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 0, right: 0, left: -25, bottom: 0 }}>
              <XAxis
                dataKey="name"
                stroke="#64748b"
                fontSize={11}
                axisLine={false}
                tickLine={false}
                dy={10}
              />
              <YAxis stroke="#64748b" fontSize={11} axisLine={false} tickLine={false} />
              <Tooltip
                cursor={{ fill: "#1e293b" }}
                contentStyle={{
                  backgroundColor: "#0f172a",
                  borderColor: "#334155",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
              <Bar dataKey="wins" name="Wins" stackId="a" fill="#22c55e" radius={[0, 0, 4, 4]} />
              <Bar dataKey="losses" name="Losses" stackId="a" fill="#ef4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
