"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const MOCK_DATA = [
  { name: "0-5%", wins: 15, losses: 20 },
  { name: "5-10%", wins: 25, losses: 15 },
  { name: "10-15%", wins: 30, losses: 10 },
  { name: "15-20%", wins: 20, losses: 5 },
  { name: "20%+", wins: 12, losses: 2 },
];

export default function EdgeHistogram() {
  return (
    <div className="card h-full flex flex-col min-h-[300px]">
      <h3 className="mb-4 text-base font-semibold text-slate-200">Edge Distribution & Outcomes</h3>
      <div className="flex-1 w-full mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={MOCK_DATA} margin={{ top: 0, right: 0, left: -25, bottom: 0 }}>
            <XAxis dataKey="name" stroke="#64748b" fontSize={11} axisLine={false} tickLine={false} dy={10} />
            <YAxis stroke="#64748b" fontSize={11} axisLine={false} tickLine={false} />
            <Tooltip
              cursor={{ fill: '#1e293b' }}
              contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
              itemStyle={{ fontSize: '12px', fontWeight: '500' }}
            />
            <Bar dataKey="wins" name="Wins" stackId="a" fill="#22c55e" radius={[0, 0, 4, 4]} />
            <Bar dataKey="losses" name="Losses" stackId="a" fill="#ef4444" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
