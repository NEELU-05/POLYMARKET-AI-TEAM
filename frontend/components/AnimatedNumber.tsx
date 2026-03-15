"use client";

import { useEffect, useState, useRef } from "react";

interface AnimatedNumberProps {
  value: number;
  format?: "currency" | "percentage" | "integer" | "decimal";
  currencySymbol?: string;
  duration?: number;
}

export default function AnimatedNumber({
  value,
  format = "integer",
  currencySymbol = "$",
  duration = 600,
}: AnimatedNumberProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const isFirstRender = useRef(true);

  useEffect(() => {
    let startTimestamp: number | null = null;
    const startValue = displayValue;
    const endValue = value;

    // Skip animation on first render if requested, or if difference is very small
    if (isFirstRender.current || startValue === endValue) {
      setDisplayValue(value);
      isFirstRender.current = false;
      return;
    }

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      
      // Ease out cubic
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      
      const currentVal = startValue + (endValue - startValue) * easeProgress;
      setDisplayValue(currentVal);

      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        setDisplayValue(endValue);
      }
    };

    window.requestAnimationFrame(step);
  }, [value, duration]);

  let formattedValue = "";
  switch (format) {
    case "currency":
      formattedValue = `${displayValue >= 0 ? "" : "-"}${currencySymbol}${Math.abs(displayValue).toFixed(2)}`;
      break;
    case "percentage":
      formattedValue = `${displayValue.toFixed(1)}%`;
      break;
    case "decimal":
      formattedValue = displayValue.toFixed(2);
      break;
    case "integer":
    default:
      formattedValue = Math.round(displayValue).toString();
      break;
  }

  // Handle forcing sign display for PnL where positive gets "+"
  if (format === "currency" && value > 0 && String(value).startsWith("+")) {
     formattedValue = `+${formattedValue}`;
  }

  return <span>{formattedValue}</span>;
}
