import * as React from "react"

import { cn } from "@/lib/utils"

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<"textarea">
>(({ className, ...props }, ref) => {
  return (
    <textarea
      className={cn(
        "flex min-h-[60px] w-full rounded-lg border border-[#E2E8F0] bg-white px-3 py-2 text-sm text-[#172033] shadow-2xs placeholder:text-[#94A3B8] focus-visible:outline-none focus-visible:border-[#0F766E] focus-visible:ring-1 focus-visible:ring-[#0F766E] disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      ref={ref}
      {...props}
    />
  )
})
Textarea.displayName = "Textarea"

export { Textarea }
