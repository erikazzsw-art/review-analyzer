"use client";

import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";

import { cn } from "@/lib/utils";

const PageTabs = TabsPrimitive.Root;

const PageTabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      "flex items-center gap-1 overflow-x-auto border-b border-line bg-white/95 px-1 backdrop-blur [-webkit-overflow-scrolling:touch]",
      className,
    )}
    {...props}
  />
));
PageTabsList.displayName = "PageTabsList";

const PageTabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "relative shrink-0 px-4 py-2.5 text-sm font-semibold text-soft transition-colors",
      "hover:text-ink",
      "data-[state=active]:text-rose",
      "after:absolute after:inset-x-0 after:bottom-0 after:h-[2px] after:scale-x-0 after:bg-rose after:transition-transform",
      "data-[state=active]:after:scale-x-100",
      className,
    )}
    {...props}
  />
));
PageTabsTrigger.displayName = "PageTabsTrigger";

const PageTabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn("mt-4 focus-visible:outline-none", className)}
    {...props}
  />
));
PageTabsContent.displayName = "PageTabsContent";

export { PageTabs, PageTabsList, PageTabsTrigger, PageTabsContent };
