import type { Territory } from "@homepedia/api-client";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const populationFormat = new Intl.NumberFormat("fr-FR");

interface TerritoriesTableProps {
  territories: readonly Territory[];
}

export function TerritoriesTable({ territories }: TerritoriesTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Code</TableHead>
          <TableHead>Commune</TableHead>
          <TableHead>Département</TableHead>
          <TableHead numeric>Population</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {territories.map((territory) => (
          <TableRow key={territory.code}>
            <TableCell>{territory.code}</TableCell>
            <TableCell>{territory.name}</TableCell>
            <TableCell>{territory.department_code ?? "—"}</TableCell>
            <TableCell numeric>
              {territory.population === null
                ? "—"
                : populationFormat.format(territory.population)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
