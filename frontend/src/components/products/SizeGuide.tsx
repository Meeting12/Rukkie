import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Ruler } from "lucide-react";

const womensSizes = [
  { size: "XS", us: "0-2", bust: "32-33", waist: "24-25", hips: "34-35" },
  { size: "S", us: "4-6", bust: "34-35", waist: "26-27", hips: "36-37" },
  { size: "M", us: "8-10", bust: "36-37", waist: "28-29", hips: "38-39" },
  { size: "L", us: "12-14", bust: "38-40", waist: "30-32", hips: "40-42" },
  { size: "XL", us: "16-18", bust: "41-43", waist: "33-35", hips: "43-45" },
  { size: "XXL", us: "20-22", bust: "44-46", waist: "36-38", hips: "46-48" },
];

const mensSizes = [
  { size: "XS", us: "32-34", chest: "34-36", waist: "28-30", hips: "34-36" },
  { size: "S", us: "36-38", chest: "36-38", waist: "30-32", hips: "36-38" },
  { size: "M", us: "38-40", chest: "38-40", waist: "32-34", hips: "38-40" },
  { size: "L", us: "42-44", chest: "42-44", waist: "36-38", hips: "42-44" },
  { size: "XL", us: "46-48", chest: "46-48", waist: "40-42", hips: "46-48" },
  { size: "XXL", us: "50-52", chest: "50-52", waist: "44-46", hips: "50-52" },
];

const shoeSizes = [
  { us: "6", uk: "5.5", eu: "38.5", cm: "24" },
  { us: "7", uk: "6.5", eu: "40", cm: "25" },
  { us: "8", uk: "7.5", eu: "41", cm: "26" },
  { us: "9", uk: "8.5", eu: "42", cm: "27" },
  { us: "10", uk: "9.5", eu: "43", cm: "28" },
  { us: "11", uk: "10.5", eu: "44.5", cm: "29" },
  { us: "12", uk: "11.5", eu: "46", cm: "30" },
];

export const SizeGuide = () => {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="link" className="p-0 h-auto text-primary">
          <Ruler className="h-4 w-4 mr-1" />
          Size Guide
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-serif text-2xl">Size Guide</DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="women" className="mt-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="women">Women</TabsTrigger>
            <TabsTrigger value="men">Men</TabsTrigger>
            <TabsTrigger value="shoes">Shoes</TabsTrigger>
          </TabsList>

          <TabsContent value="women" className="mt-4">
            <p className="text-sm text-muted-foreground mb-4">
              All measurements are in inches. If you're between sizes, we recommend sizing up.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-2 font-semibold">Size</th>
                    <th className="text-left py-3 px-2 font-semibold">US</th>
                    <th className="text-left py-3 px-2 font-semibold">Bust</th>
                    <th className="text-left py-3 px-2 font-semibold">Waist</th>
                    <th className="text-left py-3 px-2 font-semibold">Hips</th>
                  </tr>
                </thead>
                <tbody>
                  {womensSizes.map((row) => (
                    <tr key={row.size} className="border-b border-border/50">
                      <td className="py-3 px-2 font-medium">{row.size}</td>
                      <td className="py-3 px-2 text-muted-foreground">{row.us}</td>
                      <td className="py-3 px-2 text-muted-foreground">{row.bust}"</td>
                      <td className="py-3 px-2 text-muted-foreground">{row.waist}"</td>
                      <td className="py-3 px-2 text-muted-foreground">{row.hips}"</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="men" className="mt-4">
            <p className="text-sm text-muted-foreground mb-4">
              All measurements are in inches. If you're between sizes, we recommend sizing up.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-2 font-semibold">Size</th>
                    <th className="text-left py-3 px-2 font-semibold">US</th>
                    <th className="text-left py-3 px-2 font-semibold">Chest</th>
                    <th className="text-left py-3 px-2 font-semibold">Waist</th>
                    <th className="text-left py-3 px-2 font-semibold">Hips</th>
                  </tr>
                </thead>
                <tbody>
                  {mensSizes.map((row) => (
                    <tr key={row.size} className="border-b border-border/50">
                      <td className="py-3 px-2 font-medium">{row.size}</td>
                      <td className="py-3 px-2 text-muted-foreground">{row.us}</td>
                      <td className="py-3 px-2 text-muted-foreground">{row.chest}"</td>
                      <td className="py-3 px-2 text-muted-foreground">{row.waist}"</td>
                      <td className="py-3 px-2 text-muted-foreground">{row.hips}"</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="shoes" className="mt-4">
            <p className="text-sm text-muted-foreground mb-4">
              Shoe sizes may vary by brand. Please refer to specific product descriptions.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-2 font-semibold">US</th>
                    <th className="text-left py-3 px-2 font-semibold">UK</th>
                    <th className="text-left py-3 px-2 font-semibold">EU</th>
                    <th className="text-left py-3 px-2 font-semibold">CM</th>
                  </tr>
                </thead>
                <tbody>
                  {shoeSizes.map((row) => (
                    <tr key={row.us} className="border-b border-border/50">
                      <td className="py-3 px-2 font-medium">{row.us}</td>
                      <td className="py-3 px-2 text-muted-foreground">{row.uk}</td>
                      <td className="py-3 px-2 text-muted-foreground">{row.eu}</td>
                      <td className="py-3 px-2 text-muted-foreground">{row.cm}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>
        </Tabs>

        <div className="mt-6 p-4 bg-secondary/50 rounded-lg">
          <h3 className="font-semibold mb-2">How to Measure</h3>
          <ul className="text-sm text-muted-foreground space-y-1">
            <li><strong>Bust/Chest:</strong> Measure around the fullest part</li>
            <li><strong>Waist:</strong> Measure around the natural waistline</li>
            <li><strong>Hips:</strong> Measure around the fullest part of your hips</li>
          </ul>
        </div>
      </DialogContent>
    </Dialog>
  );
};
