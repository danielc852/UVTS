import { z } from 'zod';

export const MAX_PRODUCT_IMAGE_BYTES = 10 * 1024 * 1024;

export function configurationSchema(hasSavedImage: boolean) {
  return z
    .object({
      productImage: z.instanceof(File).nullable(),
      productDescription: z
        .string()
        .trim()
        .min(1, 'Describe the product before saving the question setup.'),
      totalQuestions: z.number().int().min(1).max(15),
    })
    .superRefine((value, context) => {
      if (!value.productImage && !hasSavedImage) {
        context.addIssue({
          code: 'custom',
          path: ['productImage'],
          message: 'Add a product image before saving the question setup.',
        });
      }
      if (value.productImage && !value.productImage.type.startsWith('image/')) {
        context.addIssue({
          code: 'custom',
          path: ['productImage'],
          message: 'Upload an image file.',
        });
      }
      if (value.productImage && value.productImage.size === 0) {
        context.addIssue({
          code: 'custom',
          path: ['productImage'],
          message: 'The selected image is empty. Choose another image.',
        });
      }
      if (value.productImage && value.productImage.size > MAX_PRODUCT_IMAGE_BYTES) {
        context.addIssue({
          code: 'custom',
          path: ['productImage'],
          message: 'Upload an image smaller than 10 MB.',
        });
      }
    });
}

export type ConfigurationForm = z.infer<ReturnType<typeof configurationSchema>>;
