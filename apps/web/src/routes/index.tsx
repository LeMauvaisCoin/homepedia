import { listTerritoriesOptions } from "@homepedia/api-client/react-query";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { TerritoriesTable } from "@/components/territories-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const PAGE_SIZE = 5;

const searchSchema = z.object({
  q: z.string().trim().min(1).max(80).optional().catch(undefined),
  page: z.number().int().min(1).catch(1),
});

type TerritoriesSearch = z.infer<typeof searchSchema>;

function territoriesOptions(search: TerritoriesSearch) {
  return listTerritoriesOptions({
    query: {
      q: search.q,
      limit: PAGE_SIZE,
      offset: (search.page - 1) * PAGE_SIZE,
    },
  });
}

export const Route = createFileRoute("/")({
  validateSearch: searchSchema,
  loaderDeps: ({ search }) => search,
  loader: ({ context, deps }) =>
    context.queryClient.ensureQueryData(territoriesOptions(deps)),
  component: TerritoriesPage,
});

function TerritoriesPage() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();

  const { data, isPlaceholderData } = useQuery({
    ...territoriesOptions(search),
    placeholderData: keepPreviousData,
  });

  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="flex flex-col gap-4" aria-busy={isPlaceholderData}>
      <Input
        type="search"
        aria-label="Rechercher une commune"
        placeholder="Rechercher une commune"
        defaultValue={search.q ?? ""}
        onChange={(event) => {
          void navigate({
            search: { q: event.target.value || undefined, page: 1 },
            replace: true,
          });
        }}
      />

      <TerritoriesTable territories={data?.items ?? []} />

      <footer className="flex items-center justify-between gap-4">
        <p className="text-muted-foreground text-sm" aria-live="polite">
          {total} {total === 1 ? "territoire" : "territoires"} — page{" "}
          {search.page} sur {pageCount}
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={search.page <= 1}
            onClick={() => {
              void navigate({
                search: (previous) => ({ ...previous, page: search.page - 1 }),
              });
            }}
          >
            Précédent
          </Button>
          <Button
            variant="outline"
            disabled={search.page >= pageCount}
            onClick={() => {
              void navigate({
                search: (previous) => ({ ...previous, page: search.page + 1 }),
              });
            }}
          >
            Suivant
          </Button>
        </div>
      </footer>
    </section>
  );
}
