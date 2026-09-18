import type { QueryClient } from "@tanstack/react-query";
import { Outlet, createRootRouteWithContext } from "@tanstack/react-router";

interface RouterContext {
  queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
});

function RootLayout() {
  return (
    <div className="mx-auto flex min-h-svh max-w-5xl flex-col gap-8 px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Homepedia</h1>
        <p className="text-muted-foreground text-sm">
          Exploration immobilière territoriale — jeu d’exemple local.
        </p>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
